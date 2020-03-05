// For ESP8266 WiFi APIs (including WiFi Client)
#include <ESP8266WiFi.h>

// For parsing config.json saved in SPIFFS
#include <ArduinoJson.h>
#include "FS.h"

// For UDP Multicast Listener Setup
#include <WiFiUdp.h>
#include <UdpContext.h>
#include <lwip/igmp.h>
#include <IPAddress.h>


// It's better to use StaticJsonDocument for limited RAM devices
// You can approx. the size by pasting the JSON to https://arduinojson.org/v6/assistant/
#define STATIC_JSON_SIZE 256
#define JSON_FILE_LIMIT 512
#define JSON_FILE_NAME "/config.json"
#define OTA_DEVICE_TYPE "ESP"


const char * device_id = NULL;
const char * cluster_id = NULL;
const char * ssid = NULL;
const char * passwd = "";

#define TCP_GATEWAY_SOCKET_PORT 6666

// Can probably make this a class
unsigned int buffer_size = 0;
unsigned int cmd_mcast_port = 0;
unsigned int cmd_mcast_addr[4];
char cmd_msg_separator = '|'; // The default

//States for UDP Multicast Listener
#define START_PHASE 0
#define STANDBY_PHASE 1
#define TRANSFER_PHASE 2
#define VERIFICATION_PHASE 3
#define END_PHASE 4
#define UPDATE_PHASE 5

int state = START_PHASE;

UdpContext* udp_context;
// WiFiUDP udp_socket;

bool init_runtime_params(){
  Serial.println("Reading config.json from SPIFFS...");

  File config_file = SPIFFS.open(JSON_FILE_NAME, "r");

  if (!config_file){
    Serial.println("Failed to open config.json!");
    return false;
  }

  StaticJsonDocument<STATIC_JSON_SIZE> json_doc;
  auto error = deserializeJson(json_doc, config_file);

  if(error){
    Serial.println("Failed to parse config.json!");
    return false;
  } else {
    // Change global runtime variables here
    device_id = json_doc["id"];
    cluster_id = json_doc["cluster"];

    if(!device_id){ // Device ID is null
      return false;
    }

    if(json_doc.containsKey("ssid")){
      ssid = json_doc["ssid"];
    }

    if(json_doc.containsKey("passwd")){
      passwd = json_doc["passwd"];
    }
    
    return true;
  }
}

void scan_for_open_wifi(){
  ssid = "default_value";

  // Connect to the one with highest RSSI
  int detected_ssid = WiFi.scanNetworks();

  if (detected_ssid == 0){
    Serial.println("No network detected!");
  }
  else{
    int max_rssi = 0;
    int chosen_ssid_idx = detected_ssid;

    for (int ctr = 0; ctr < detected_ssid; ++ctr){
      if (WiFi.encryptionType(ctr) != ENC_TYPE_NONE){
        continue;
      }

      if (max_rssi < WiFi.RSSI(ctr)){
        max_rssi = WiFi.RSSI(ctr);
        chosen_ssid_idx = ctr;
      }
    }

    if (chosen_ssid_idx != detected_ssid){
      ssid = WiFi.SSID(chosen_ssid_idx).c_str();
    }
  }
}

bool connect_to_wifi(){
  // Set to station mode and disconnect from last connected AP
  WiFi.mode(WIFI_STA);
  WiFi.disconnect();

  // Check if SSID is defined in config.json
  if(!ssid){
    Serial.println("No SSID defined in config.json!");
    Serial.println("Scanning for open WiFi networks!");

    // TODO: Can fallback to SoftAP mode for advanced configurations later
    // Scan for any available open SSID using WiFiScan
    // and connect to the one with the highest RSSI
    scan_for_open_wifi();
  }

  Serial.print("Connecting to ");
  Serial.println(ssid);
  WiFi.begin(ssid, passwd);

  while(WiFi.status() != WL_CONNECTED){
    delay(300);
    Serial.print(".");
  }

  Serial.println("");

  Serial.print("Connected to ");
  Serial.println(ssid);

  Serial.print("IP Address : ");
  Serial.println(WiFi.localIP());
  // Then connect to the one with the best RSSI
  
  return true;
}

bool init_to_gateway(){
  WiFiClient tcp_client;
  tcp_client.setNoDelay(true);

  // For this case, we use the gateway IP
  bool is_connected = tcp_client.connect(WiFi.gatewayIP().toString().c_str(), TCP_GATEWAY_SOCKET_PORT);
  bool gateway_init_success = false;

  if(is_connected){
    // Create JSON to send
    StaticJsonDocument<STATIC_JSON_SIZE> json_req;

    json_req["id"] = device_id;
    json_req["cluster"] = cluster_id;
    json_req["type"] = OTA_DEVICE_TYPE;

    // Serialize minified JSON into String
    String temp_buf;
    serializeJson(json_req, temp_buf);

    // Send via TCP Socket stream
    tcp_client.println(temp_buf);

    // Wait for Gateway's reply
    const char *gateway_reply = "";

    while (tcp_client.connected() || tcp_client.available()){
      if(tcp_client.available()){
        gateway_reply = tcp_client.readStringUntil('\n').c_str();
      }
    }

    StaticJsonDocument<STATIC_JSON_SIZE> json_reply;
    auto err = deserializeJson(json_reply, gateway_reply);

    if(err){
      Serial.println("ArduinoJSON deserialization error!");
      Serial.println(err.c_str());
    } else {
      if(json_reply["status"].as<String>() == String("success")){
        // Use Explicit Casting
        buffer_size = json_reply["buffer"].as<int>();
        cmd_msg_separator = json_reply["msg_separator"].as<char>();
        cmd_mcast_port = json_reply["cmd_mcast_port"].as<int>();

        // Implicit casting here
        char* addr_string = json_reply["cmd_mcast_addr"];

        char* temp = strtok(addr_string, ".");
        for(int octet = 0; octet < 4; octet++){
          if(temp != NULL){
            cmd_mcast_addr[octet] = int(temp);
            temp = strtok(NULL, ".");
          }
        }
      }
      
      gateway_init_success = true;
    }
  } else {
    Serial.println("Failed to connect to Gateway!");
  }

  return gateway_init_success;
}

bool set_mcast_listener(){
  if(udp_context){
    udp_context->unref();
    udp_context = 0;
  }

  // Joins IGMP Group first
  const char* local_ip_string = WiFi.localIP().toString().c_str();
  char* holder;
  int temp[4];

  holder = strtok((char*)local_ip_string, ".");
  for(int idx=0; idx < 4; idx++){
    if(holder != NULL){
      temp[idx] = int(holder);
      holder = strtok(NULL, ".");
    }
  }

  ip_addr* local_ip;
  IP4_ADDR(local_ip, temp[0], temp[1], temp[2], temp[3]);

  ip_addr* mcast_addr;
  IP4_ADDR(mcast_addr, cmd_mcast_addr[0], cmd_mcast_addr[1], cmd_mcast_addr[2], cmd_mcast_addr[3]);
  if (igmp_joingroup(local_ip, mcast_addr) != ERR_OK)
  {
    return false;
  }

  udp_context = new UdpContext;
  udp_context->ref();

  // Set custom packet listener
  udp_context->onRx(&on_mcast_cmd_packet);

  // TODO: FIX THIS
  if(!udp_context->listen(IPADDR4_INIT(INADDR_ANY), cmd_mcast_port)){
    return false;
  }

  state = STANDBY_PHASE;
  return true;
}

void on_mcast_cmd_packet(){
  if (state == STANDBY_PHASE) {
  } else if (state == TRANSFER_PHASE){
  } else if (state == VERIFICATION_PHASE){
  } else if (state == END_PHASE){
  } else if (state == UPDATE_PHASE){
  } 
}

void apply_update(){
  // TODO: Base this on Updater Class used in ArduinoOTA
}

void handle_ota_service(){
  if(state == UPDATE_PHASE){
    apply_update();
    state = STANDBY_PHASE;
  }
}

void setup() {
  Serial.begin(9600);

  bool init_params_success = false;

  if (SPIFFS.exists(JSON_FILE_NAME)){
    // Read config.json to initialize global variables
    init_params_success = init_runtime_params();
  } else {
    Serial.println("config.json File does not exists in SPIFFS!");
  }
  

  // Handles connecting to WiFi
  // Might loop indefinitely, indicating no respnse from SSID
  // Or no available open SSID detected
  bool gateway_wifi_connected = connect_to_wifi();


  bool init_gateway_success = false;
  // If successfully connected to WiFi (and Device ID Defined)
  // try to initialize to TCP Socket Server
  if(init_params_success && gateway_wifi_connected){
    init_gateway_success = init_to_gateway();
  } else {
    Serial.println("OTA Service Unavailable!");
  }

  // If successfully initialized to gateway, setup Async Multicast Listener
  if(init_gateway_success){
    set_mcast_listener();
    Serial.println("Starting OTA Service Listener...");
  }
}

void loop() {
  handle_ota_service();
  // put your main code here, to run repeatedly:

}
