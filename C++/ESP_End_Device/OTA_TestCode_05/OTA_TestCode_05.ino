// For ESP8266 WiFi APIs (including WiFi Client)
#include "user_interface.h"
#include <ESP8266WiFi.h>
#include <WiFiUdp.h>

// For parsing config.json saved in SPIFFS
#include <ArduinoJson.h>
#include "FS.h"

// For UDP Multicast Listener Setup
#include "lwip/ip_addr.h"
#include "lwip/ip4_addr.h"
#include "lwip/igmp.h"
#include "lwip/udp.h"
#include "lwip/inet.h"
#include "include/UdpContext.h"

// Firmware Update Handler for ESP8266 Core
#define DEBUG_UPDATER Serial // For Updater.h process debugging
#include <Updater.h>
#include <MD5Builder.h>

// It's better to use StaticJsonDocument for limited RAM devices
// You can approx. the size by pasting the JSON to https://arduinojson.org/v6/assistant/
#define STATIC_JSON_SIZE 256
#define JSON_FILE_NAME "/config.json"
#define OTA_DEVICE_TYPE "ESP"

String device_id;
String cluster_id;
char update_type =  NULL;

// Can probably make this a class/struct
unsigned int buffer_size = 0;
unsigned int data_timeout = 0;
char cmd_msg_separator = '|'; // The default
String data_mcast_addr;

//States for UDP Multicast Listener
#define START_PHASE 0
#define STANDBY_PHASE 1
#define TRANSFER_PHASE 2
#define VERIFICATION_PHASE 3
#define END_PHASE 4
#define UPDATE_PHASE 5
#define DONE_UPDATE 6

int state = START_PHASE;

UdpContext* cmd_udp_context;
UdpContext* data_udp_context;

MD5Builder* md5_checksum;
String server_checksum;

#define CMD_READY_FOR_TRANSFER "OK"
#define CMD_INSUFFICIENT_SPACE "NO"
#define CMD_PROCESS_ERROR "FA"

#define CMD_TRANSFER_SUCCESS  "ACK"
#define CMD_CHECKSUM_MISMATCH "NEQ"
#define CMD_DATA_TIMEOUT "DTO"

#define DATA_TIMEOUT_VAL 50 // 50 times 10ms check

// User #define-s
#define RED_LED_PIN D1
#define GREEN_LED_PIN D2

//Fancy Blinking

// Only a wrapper for ease of access
// Will be run in the setup() section
void user_setup(){
  pinMode(GREEN_LED_PIN, OUTPUT);
  pinMode(RED_LED_PIN, OUTPUT);
}

// Only a wrapper for ease of access
// Will be run in the loop() section
void user_loop(){
  digitalWrite(GREEN_LED_PIN, HIGH);
  digitalWrite(RED_LED_PIN, HIGH);
  delay(250);
  digitalWrite(GREEN_LED_PIN, LOW);
  digitalWrite(RED_LED_PIN, HIGH);
  delay(250);
  digitalWrite(GREEN_LED_PIN, HIGH);
  digitalWrite(RED_LED_PIN, LOW);
  delay(250);
  digitalWrite(GREEN_LED_PIN, LOW);
  digitalWrite(RED_LED_PIN, LOW);
  delay(250);
}

// Scans for open WiFi Networks, connects to the one with highest RSSI, if any
// Returns connected SSID
// Defaults to "random_ssid" if none available
String scan_for_open_wifi(){
  String curr_ssid = "";
  int detected_ssid = WiFi.scanNetworks();

  if (detected_ssid == 0){
    Serial.println("No network detected!");
  } else {
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
      // Connect to the one with highest RSSI
      curr_ssid = WiFi.SSID(chosen_ssid_idx);
    } else {
      curr_ssid = "random_ssid";
    }
  }

  return curr_ssid;
}

// Handles initial WiFi Connection
// Will attempt to connect to best open WiFi (based on RSSI)
// to ensure application can still run even if not connected to gateway
bool connect_to_wifi(String ssid, String passwd){
  // Set to station mode and disconnect from last connected AP
  WiFi.mode(WIFI_STA);
  // wifi_set_sleep_type(NONE_SLEEP_T);
  WiFi.disconnect();

  if(!ssid || !passwd){
    Serial.println("No SSID defined in config.json!");
    Serial.println("Scanning for open WiFi networks!");

    // Scan for any available open SSID using WiFiScan
    // and connect to the one with the highest RSSI
    ssid = scan_for_open_wifi();
    passwd = "";
  } else {
    Serial.println("Using SSID from config.json...");
  }
  
  WiFi.begin(ssid, passwd);

  // Will loop indefinitely while not connected
  while(WiFi.status() != WL_CONNECTED){
    delay(500);
  }

  Serial.println("");

  Serial.print("Connected to ");
  Serial.println(ssid);

  Serial.print("IP Address : ");
  Serial.println(WiFi.localIP());
  
  return true;
}

// Clean up function for data_udp_context
// Called when successfully received all data
// Or if received abort command
//TODO: Error -6 leaving IGMP Group, check it
void discard_data_context(){
  // Leave the IGMP group
  ip_addr* mcast_addr = new ip_addr;
  mcast_addr->addr = ipaddr_addr(data_mcast_addr.c_str());

  ip_addr* local_addr = new ip_addr;
  local_addr->addr = ipaddr_addr(WiFi.localIP().toString().c_str());

  for(int attempts = 0; attempts < 3; attempts++){
    int err_code = igmp_leavegroup(local_addr, mcast_addr);

    if (err_code != ERR_OK){
      Serial.print("IGMP Leave Group Error Code : ");
      Serial.println(err_code);
    }
  }

  // Cleanup using UdpContext's methods
  if (data_udp_context){
    data_udp_context->unref();
    data_udp_context = 0;
  }

  buffer_size = 0;
}

// Based on ArduinoOTA's readStringUntil
// Reads until the specified cmd_msg_separator, or \0 or \n character
String parse_cmd(){
  String holder;
  int val;

  while(true){
    val = cmd_udp_context->read();
    char char_cast = char(val);

    if(val < 0 || char_cast == '\0' || char_cast == cmd_msg_separator || char_cast == '\n'){
      break;
    } 

    holder += char_cast;
  }

  return holder;
}

// Constructs and sends reply message to Command Multicast Address
void reply_cmd(String msg[], int arr_length){
  String holder = "";
  holder += msg[0];

  for(int idx = 1; idx < arr_length; idx++){
    holder += cmd_msg_separator;
    holder += msg[idx];
  }

  holder += '\n';
  Serial.print("Reply to Gateway : ");
  Serial.println(holder);

  cmd_udp_context->append(holder.c_str(), holder.length());
  cmd_udp_context->send(cmd_udp_context->getRemoteAddress(), cmd_udp_context->getRemotePort());
}

// Cleanup and reset globals
// Called on abort command, or when all is complete
void cleanup_states(){
  Update.end();

  discard_data_context();
  data_timeout = DATA_TIMEOUT_VAL;
  state = STANDBY_PHASE;
  update_type = NULL;
  data_mcast_addr = String();
  delete md5_checksum;
  ESP.reset();
}

// Receive UDP datagram from Data Multicast Address
// to be bound to UdpContext onRx
void on_recv_data(){
  if(!data_udp_context->next() || buffer_size == 0){
    return;
  }

  data_timeout = DATA_TIMEOUT_VAL;

  size_t data_size = min(buffer_size, data_udp_context->getSize());
  unsigned char temp_buf[data_size];
  size_t read_size = data_udp_context->read((char *)temp_buf, data_size);

  md5_checksum->add((uint8_t*)temp_buf, read_size);
  Update.write(temp_buf, read_size);

  while(data_udp_context->next()){
    data_udp_context->flush();
  }

  if (Update.isFinished()){
    state = VERIFICATION_PHASE;
  }
}

// Receive UDP datagram from Command Multicast Address
// to be bound to UdpContext onRx
void on_cmd_mcast_packet(){
  if(!cmd_udp_context->next()){
    return;
  }

  String cmd_message = parse_cmd();
  String target_id = parse_cmd();

  if(update_type != NULL){
    // Return early if not for me
    // Only check this if update_type is defined
    if (update_type != 'c' && update_type != 'd'){
      return;
    } else if (update_type == 'c' && (!cluster_id || !cluster_id.equals(target_id))){
      return;
    } else if (update_type == 'd' && !device_id.equals(target_id)){
      return;
    }
  }

  if(cmd_message == "a"){
    String cmd_source = parse_cmd();
    Serial.print("Received Abort Command from Gateway ");
    Serial.println(cmd_source);

    cleanup_states();
    return;
  }
  
  if (state == STANDBY_PHASE) {
    Serial.println("Command Received in Standby Phase!");
    
    if(!cmd_message.equals("c") && !cmd_message.equals("d")){
      return;
    }

    Serial.println("Hey");
    // If pass all the above checks
    // cmd_message should contain update type [d = device, c = cluster]
    update_type = cmd_message[0];

    // Third part is the file size, to be parsed to int
    size_t file_size = parse_cmd().toInt();

    if(!Update.begin(file_size, U_FLASH)){
      // Replies with 2 part message to notify gateway
      Update.printError(Serial);

      const char* err_code;
      if(Update.getError() == UPDATE_ERROR_SPACE){
        err_code = CMD_INSUFFICIENT_SPACE;
      } else {
        err_code = CMD_PROCESS_ERROR;
      }
      String error_msg[2] = {err_code, device_id};
      reply_cmd(error_msg, 2);
      return;
    }

    Update.runAsync(true);

    // Calculate possible buffer size (based on Update.cpp internal implementation)
    // Default value from Updater.cpp is 256

    // Fourth and fifth part are multicast address and port (respectively)
    // to be used for data transfer later
    data_mcast_addr = parse_cmd();
    unsigned int data_mcast_port = parse_cmd().toInt();

    // Create another multicast listener with UdpContext and set listener
    set_mcast_listener("data", data_mcast_addr, data_mcast_port);

    String possible_buffer = String(UDP_TX_PACKET_MAX_SIZE);
    // String possible_buffer = String((ESP.getFreeHeap() > (2 * FLASH_SECTOR_SIZE)) ? FLASH_SECTOR_SIZE : 256);

    // Replies with 3 part message if all is good
    // The third part specifies buffer size that this device can handle
    String success_reply_msg[3] = {CMD_READY_FOR_TRANSFER, device_id, possible_buffer};
    reply_cmd(success_reply_msg, 3);

    state = TRANSFER_PHASE;
  } else if (state == TRANSFER_PHASE){
    Serial.println("Command Received in Transfer Phase!");
    if(!cmd_message.equals("t")){
      return;
    }

    server_checksum = parse_cmd();
    Serial.print("Received Checksum : ");
    Serial.println(server_checksum);

    md5_checksum = new MD5Builder();
    md5_checksum->begin();
    //Update.setMD5(md5_checksum.c_str());

    // Use this buffer_size for receiving data
    buffer_size = parse_cmd().toInt();
    Serial.print("Ready to receive data (");
    Serial.print(buffer_size);
    Serial.println(" bytes)");
    data_timeout = DATA_TIMEOUT_VAL;

    // Does not change state here to make sure
    // This is to make sure that VERIFICATION_PHASE only starts after all data are received
  } else if (state == END_PHASE){
    Serial.println("Command Received in End Phase!");

    if(!cmd_message.equals("s")){
      return;
    }

    state = UPDATE_PHASE;
  }

  while (cmd_udp_context->next()){
    cmd_udp_context->flush();
  }
}

// Creates Multicast Listener and bind to UdpContext
bool set_mcast_listener(String target_ctx, String target_mcast_addr, unsigned int target_mcast_port){
  if (target_ctx.equals("cmd")){
    if(cmd_udp_context){
      cmd_udp_context->unref();
      cmd_udp_context = 0;
    }
  } else if(target_ctx.equals("data")){
    if (data_udp_context){
      data_udp_context->unref();
      data_udp_context = 0;
    }
  } else {
    return false;
  }

  ip_addr* mcast_addr = new ip_addr;
  mcast_addr->addr = ipaddr_addr(target_mcast_addr.c_str());

  ip_addr* local_addr = new ip_addr;
  local_addr->addr = ipaddr_addr(WiFi.localIP().toString().c_str());

  // Joins IGMP Group first
  for(int attempts = 0; attempts < 3; attempts++){
    int err_code = igmp_joingroup(local_addr, mcast_addr);

    if (err_code != ERR_OK){
      Serial.print("IGMP Join Group Error Code : ");
      Serial.println(err_code);
      return false;
    }
  }

  if (target_ctx.equals("cmd")){
    cmd_udp_context = new UdpContext;
    cmd_udp_context->ref();

    // Set custom packet listener
    if (!cmd_udp_context->listen(IPADDR4_INIT(INADDR_ANY), target_mcast_port)){
      return false;
    }

    cmd_udp_context->onRx(&on_cmd_mcast_packet);
  }
  else if (target_ctx.equals("data")){
    data_udp_context = new UdpContext;
    data_udp_context->ref();

    // Set custom packet listener
    if (!data_udp_context->listen(IPADDR4_INIT(INADDR_ANY), target_mcast_port)){
      return false;
    }
    
    data_udp_context->onRx(&on_recv_data);
  }
  else{
    return false;
  }

  Serial.print("Listening for ");
  Serial.print(target_ctx);
  Serial.print(" at address ");
  Serial.println(target_mcast_addr);

  return true;
}

// Reads config.json and set global variables accordingly
// Returns the TCP port used to connect to Gateway's TCP Socket
// Returns 0 if failed
int init_runtime_params(){
  // Initial call to SPIFFS before reading config
  int tcp_port = 0;

  if(!SPIFFS.begin()){
    Serial.println("Failed to mount SPIFFS!");
  } else {
    Serial.println("Reading config.json from SPIFFS...");

    File config_file = SPIFFS.open(JSON_FILE_NAME, "r");

    if (!config_file){
      Serial.println("Failed to open config.json!");
    } else {
      StaticJsonDocument<STATIC_JSON_SIZE> json_doc;
      auto error = deserializeJson(json_doc, config_file);
      
      // Unmount SPIFFS since we're done with the files
      SPIFFS.end();

      if(error){
        Serial.println("Failed to parse config.json!");
      } else {
        // Change global runtime variables here
        device_id = json_doc["id"].as<String>();

        if(device_id){ // Device ID is not null
          cluster_id = (json_doc["cluster"].is<String>()) ? json_doc["cluster"].as<String>() : String();

          if(connect_to_wifi(json_doc["ssid"].as<String>(), json_doc["passwd"].as<String>())){
            tcp_port = json_doc["tcp_gw_port"].as<int>() | 6666; //The default value
          }
        }
      }
    }
  }

  return tcp_port;
}

// If successfully connected to WiFi (and Device ID Defined)
// try to initialize to TCP Socket Server
bool init_to_gateway(int tcp_port){
  WiFiClient tcp_client;
  tcp_client.setNoDelay(true);

  // For this case, we use the gateway IP
  bool is_connected = tcp_client.connect(WiFi.gatewayIP().toString().c_str(), tcp_port);
  bool gateway_init_success = false;

  if(!tcp_client.connected()){
    Serial.println("Failed to connect to Gateway!");
  } else {
    // Create JSON to send
    StaticJsonDocument<STATIC_JSON_SIZE> json_req;

    json_req["code"] = "INIT";
    json_req["id"] = device_id;
    json_req["cluster"] = cluster_id;
    json_req["type"] = OTA_DEVICE_TYPE;

    // Send Serialized JSON to TCP Server
    tcp_client.println(json_req.as<String>());

    // Receive Serialized JSON Reply
    StaticJsonDocument<STATIC_JSON_SIZE> json_reply;
    auto err = deserializeJson(json_reply, tcp_client);

    // Stop and disconnect, since we're done using it
    tcp_client.stop();

    if(err){
      Serial.println("ArduinoJSON deserialization error!");
      Serial.println(err.c_str());
    } else {
      String response_status = json_reply["status"].as<String>();
      
      if(!response_status){
        Serial.println("Bad JSON Response from Gateway!");
      } else if(response_status.equals("success")){
        Serial.println(json_reply["msg_separator"].as<char>());
        cmd_msg_separator = json_reply["msg_separator"].as<char>() | '|';

        gateway_init_success = set_mcast_listener("cmd", json_reply["cmd_mcast_addr"].as<String>(), json_reply["cmd_mcast_port"].as<unsigned int>());
      } else {
        Serial.println("Failed to initialize OTA Service for device!");
      }
    }
  }

  return gateway_init_success;
}

// An extension to set_mcast_listener function
// Handles some Phases of the OTA (Verification & Update)
void handle_ota_service(){
  // Get rid of this first, cause it's making problems
  if(state == TRANSFER_PHASE){
    // Checks whether the Data Mcast Listener timed out
    if(data_timeout > 0){
      delay(10);
      data_timeout--;
    } else {
      // Considers the gateway already in VERIFICATION_PHASE
      // Tells them we timedout
      String reply_msg[2] = {CMD_DATA_TIMEOUT, device_id};
      reply_cmd(reply_msg, 2);

      data_timeout = DATA_TIMEOUT_VAL;
    }
  } else if(state == VERIFICATION_PHASE){
    Serial.println("Verifying Checksum...");
    md5_checksum->calculate();
    bool checksum_mismatch = !md5_checksum->toString().equals(server_checksum);

    String reply_code = (checksum_mismatch) ? CMD_CHECKSUM_MISMATCH : CMD_TRANSFER_SUCCESS;
    String reply_msg[2] = {reply_code, device_id};
    reply_cmd(reply_msg, 2);

    state = END_PHASE;
  } else if(state == UPDATE_PHASE){
    Serial.println("Applying Updates...");
    cleanup_states();
  }
}

void setup() {
  Serial.begin(115200);
  Serial.println("");

  // Read config.json to initialize global variables
  int tcp_port = init_runtime_params();
  if (tcp_port == 0){
    Serial.println("config.json File does not exists in SPIFFS!");
  }

  bool init_gateway_success = init_to_gateway(tcp_port);
  if(tcp_port == 0 || !init_gateway_success){
    Serial.println("OTA Service Unavailable!");
  }

  // If successfully initialized to gateway, setup Async Multicast Listener
  if(init_gateway_success){
    Serial.println("Starting OTA Service Listener...");
    state = STANDBY_PHASE;
  }

  // User setup here
  user_setup();
}

void loop() {
  handle_ota_service();

  // User code here
  user_loop();
}
