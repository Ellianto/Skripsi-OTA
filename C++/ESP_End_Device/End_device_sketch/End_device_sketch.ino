// For ESP8266 WiFi APIs (including WiFi Client)
#include <ESP8266WiFi.h>

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

// It's better to use StaticJsonDocument for limited RAM devices
// You can approx. the size by pasting the JSON to https://arduinojson.org/v6/assistant/
#define STATIC_JSON_SIZE 256
#define JSON_FILE_LIMIT 512
#define JSON_FILE_NAME "/config.json"
#define OTA_DEVICE_TYPE "ESP"

char update_type;
String device_id;
String cluster_id;
String ssid;
String passwd;

#define TCP_GATEWAY_SOCKET_PORT 6666

// Can probably make this a class/struct
unsigned int buffer_size = 0; 
unsigned int cmd_mcast_port = 0;
String cmd_mcast_addr;
String data_mcast_addr;
char cmd_msg_separator = '|'; // The default

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

#define CMD_READY_FOR_TRANSFER "OK"
#define CMD_INSUFFICIENT_SPACE "NO"
#define CMD_PROCESS_ERROR "FA"

#define CMD_TRANSFER_SUCCESS "ACK"
#define CMD_CHECKSUM_MISMATCH "NEQ"

// Reads config.json and set global variables accordingly
bool init_runtime_params(){
  // Initial call to SPIFFS before reading config
  if(!SPIFFS.begin()){
    Serial.println("Failed to mount SPIFFS!");
  }
  
  Serial.println("Reading config.json from SPIFFS...");

  File config_file = SPIFFS.open(JSON_FILE_NAME, "r");

  if (!config_file){
    Serial.println("Failed to open config.json!");
    return false;
  }

  StaticJsonDocument<STATIC_JSON_SIZE> json_doc;
  auto error = deserializeJson(json_doc, config_file);
  
  // Unmount SPIFFS since we're done with the files
  SPIFFS.end();

  if(error){
    Serial.println("Failed to parse config.json!");
    return false;
  } else {
    // Change global runtime variables here
    device_id = String(json_doc["id"].as<const char*>());
    cluster_id = String(json_doc["cluster"].as<const char *>());

    if(!device_id){ // Device ID is null
      return false;
    }

    if(json_doc.containsKey("ssid")){
      Serial.println("Using SSID from config.json...");
      ssid = String(json_doc["ssid"].as<const char*>());
    }

    if(json_doc.containsKey("passwd")){
      passwd = String(json_doc["passwd"].as<const char*>());
    }
    
    return true;
  }
}

// Scans for available WiFi Networks and their RSSI
// Connects to open WiFi with highest RSSI, if any.
// Will connect to "random_ssid" if none available
// WIll be called when config.json doesn't specify SSID
void scan_for_open_wifi(){
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
      ssid = WiFi.SSID(chosen_ssid_idx);
    } else {
      ssid = "random_ssid";
    }
  }
}

// Handles initial WiFi Connection
// Will attempt to connect to best open WiFi (based on RSSI)
// to ensure application can still run even if not connected to gateway
bool connect_to_wifi(){
  // Set to station mode and disconnect from last connected AP
  WiFi.mode(WIFI_STA);
  WiFi.disconnect();

  if(!ssid){
    Serial.println("No SSID defined in config.json!");
    Serial.println("Scanning for open WiFi networks!");

    // Scan for any available open SSID using WiFiScan
    // and connect to the one with the highest RSSI
    scan_for_open_wifi();
  }
  
  WiFi.begin(ssid, passwd);

  // Will loop indefinitely while not connected
  while(WiFi.status() != WL_CONNECTED){
    delay(500);
    Serial.print('.');
  }

  Serial.println("");

  Serial.print("Connected to ");
  Serial.println(ssid);

  Serial.print("IP Address : ");
  Serial.println(WiFi.localIP());
  
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

    json_req["code"] = "INIT";
    json_req["id"] = device_id;
    json_req["cluster"] = cluster_id;
    json_req["type"] = OTA_DEVICE_TYPE;

    // Serialize minified JSON into String
    String temp_buf;
    serializeJson(json_req, temp_buf);

    // Send via TCP Socket stream
    tcp_client.println(temp_buf);

    // Wait for Gateway's reply
    char *gateway_reply = "";

    while (tcp_client.connected() || tcp_client.available()){
      if(tcp_client.available()){
        strcat(gateway_reply, tcp_client.readStringUntil('\n').c_str());
      }
    }

    StaticJsonDocument<STATIC_JSON_SIZE> json_reply;
    auto err = deserializeJson(json_reply, gateway_reply);

    if(err){
      Serial.println("ArduinoJSON deserialization error!");
      Serial.println(err.c_str());
    } else {
      if(!json_reply.containsKey("status")){
        Serial.println('Bad JSON Response from Gateway!');
      } else if(json_reply["status"].as<const char*>() == "success"){
        // Use Explicit Casting
        buffer_size = json_reply["buffer"].as<int>();
        cmd_msg_separator = json_reply["msg_separator"].as<char>();
        cmd_mcast_port = json_reply["cmd_mcast_port"].as<int>();

        // Implicit casting here
        cmd_mcast_addr = String(json_reply["cmd_mcast_addr"].as<const char*>());
        gateway_init_success = true;
      } else {
        Serial.println("Failed to initialize OTA Service for device!");
      }
      
    }
  } else {
    Serial.println("Failed to connect to Gateway!");
  }

  return gateway_init_success;
}

// Creates Multicast Listener and bind to UdpContext
bool set_mcast_listener(UdpContext* target_udp_ctx, String target_mcast_addr, unsigned int target_mcast_port){
  if (target_udp_ctx){
    target_udp_ctx->unref();
    target_udp_ctx = 0;
  }

  int temp_arr[4]; 
  int* local_ip_octets = parse_ipv4_addr(temp_arr, WiFi.localIP().toString());
  ip4_addr_t* local_ip;
  IP4_ADDR(local_ip, local_ip_octets[0], local_ip_octets[1], local_ip_octets[2], local_ip_octets[3]);

  int another_arr[4];
  int* mcast_ip_octets = parse_ipv4_addr(another_arr, target_mcast_addr);
  ip4_addr_t* mcast_addr;
  IP4_ADDR(mcast_addr, mcast_ip_octets[0], mcast_ip_octets[1], mcast_ip_octets[2], mcast_ip_octets[3]);

  // Joins IGMP Group first
  for(int attempts = 0; attempts < 3; attempts++){
    int err_code = igmp_joingroup(local_ip, mcast_addr);

    if (err_code != ERR_OK){
      Serial.print("IGMP Join Group Error Code : ");
      Serial.println(err_code);
      return false;
    }
  }

  target_udp_ctx = new UdpContext;
  target_udp_ctx->ref();

  // Set custom packet listener
  if (!target_udp_ctx->listen(IPADDR4_INIT(INADDR_ANY), target_mcast_port)){
    return false;
  }

  return true;
}

// Clean up function for data_udp_context
// Called when successfully received all data
// Or if received abort command
void discard_data_context(){
  // Leave the IGMP group
  int temp_arr[4];
  int *local_ip_octets = parse_ipv4_addr(temp_arr, WiFi.localIP().toString());
  ip4_addr_t *local_ip;
  IP4_ADDR(local_ip, local_ip_octets[0], local_ip_octets[1], local_ip_octets[2], local_ip_octets[3]);

  int another_arr[4];
  int *mcast_ip_octets = parse_ipv4_addr(another_arr, data_mcast_addr);
  ip4_addr_t *mcast_addr;
  IP4_ADDR(mcast_addr, mcast_ip_octets[0], mcast_ip_octets[1], mcast_ip_octets[2], mcast_ip_octets[3]);

  for(int attempts = 0; attempts < 3; attempts++){
    int err_code = igmp_leavegroup(local_ip, mcast_addr);

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

// Parse %d.%d.%d.%d to int[4]
int *parse_ipv4_addr(int *holder, String addr_string){
  char *octet = strtok((char *)addr_string.c_str(), ".");

  for (int idx = 0; idx < 4; idx++){
    if (octet != NULL)
      continue;

    holder[idx] = int(octet);
    octet = strtok(NULL, ".");
  }

  return holder;
}

bool should_listen(const char* received_id){
  bool for_me = true;
  String target_id = String(received_id);
  
  if (update_type == 'c'){
    if (!cluster_id || cluster_id != target_id){
      for_me = false;
    }
  }
  else if (update_type == 'd'){
    if (target_id != device_id){
      for_me = false;
    }
  }

  return for_me;
}

// Calculate possible buffer size (based on Update.cpp internal implementation)
size_t calculate_buffer(){
  // Default value from Updater.cpp is 256
  return (ESP.getFreeHeap() > 2 * FLASH_SECTOR_SIZE) ? FLASH_SECTOR_SIZE : 256;
}

// Based on ArduinoOTA's readStringUntil
const char* parse_cmd(char delimiter){
  String holder;
  int val;

  while(true){
    val = cmd_udp_context->read();

    if(val < 0 || val == '\0' || val == delimiter){
      break;
    } 

    holder += static_cast<char>(val);
  }

  return holder.c_str();
}

// Constructs and sends reply message to Command Multicast Address
void reply_cmd(const char* msg[], int arr_length, char delimiter){
  String holder = "";
  holder += msg[0];

  for(int idx = 1; idx < arr_length; idx++){
    holder += delimiter;
    holder += msg[idx];
  }

  holder += '\n';

  cmd_udp_context->append(holder.c_str(), holder.length());

//  ip_addr_t *remote_ip = (ip_addr_t *)cmd_udp_context->getRemoteAddress();
  uint16_t remote_port = cmd_udp_context->getRemotePort();
  cmd_udp_context->send(cmd_udp_context->getRemoteAddress(), remote_port);

  return;
}

// Receive UDP datagram from Data Multicast Address
// to be bound to UdpContext onRx
void on_recv_data(){
  if(!data_udp_context->next() || buffer_size == 0){
    return;
  }

  char* temp_buf;
  size_t read_len = (buffer_size <= data_udp_context->getSize()) ? buffer_size : data_udp_context->getSize();
  size_t read_size = data_udp_context->read(temp_buf, read_len);
  // TODO: Lets hope the casting works
  Update.write((uint8_t*)temp_buf, read_size);

  while(data_udp_context->next()){
    data_udp_context->flush();
  }

  if (Update.isFinished()){
    discard_data_context();
    state = VERIFICATION_PHASE;
  }
}

// Receive UDP datagram from Command Multicast Address
// to be bound to UdpContext onRx
void on_cmd_mcast_packet(){
  if(!cmd_udp_context->next()){
    return;
  }

  const char* cmd_message = parse_cmd(cmd_msg_separator);
  const char* target_id = parse_cmd(cmd_msg_separator);

  if(!should_listen(target_id)){
    return;
  }

  if(cmd_message == "a"){
    const char* cmd_source = parse_cmd('\n');
    Serial.print("Received Abort Command from Gateway ");
    Serial.println(cmd_source);

    Update.end();

    discard_data_context();
    state = STANDBY_PHASE;
    return;
  }
  
  if (state == STANDBY_PHASE) {
    if(cmd_message != "c" && cmd_message != "d"){
      return;
    }

    Serial.println("Command Received in Standby Phase!");
    // If pass all the above checks
    // cmd_message should contain update type [d = device, c = cluster]
    update_type = cmd_message[0];

    // Third part is the file size, to be parsed to int
    size_t file_size = atoi(parse_cmd(cmd_msg_separator));

    if(!Update.begin(file_size, U_FLASH)){
      // Replies with 2 part message to notify gateway
      Update.printError(Serial);

      const char* err_code;
      if(Update.getError() == UPDATE_ERROR_SPACE){
        err_code = CMD_INSUFFICIENT_SPACE;
      } else {
        err_code = CMD_PROCESS_ERROR;
      }
      const char* error_msg[2] = {err_code, device_id.c_str()};
      reply_cmd(error_msg, 2, cmd_msg_separator);
      return;
    }

    size_t possible_buffer = calculate_buffer();

    // Fourth and fifth part are multicast address and port (respectively)
    // to be used for data transfer later
    data_mcast_addr = String(parse_cmd(cmd_msg_separator));
    const char* data_mcast_port = parse_cmd('\n');

    // Create another multicast listener with UdpContext and set listener
    set_mcast_listener(data_udp_context, data_mcast_addr, atoi(data_mcast_port));
    data_udp_context->onRx(&on_recv_data);

    char* buf_size;
    itoa(possible_buffer, buf_size, 10);

    // Replies with 3 part message if all is good
    // The third part specifies buffer size that this device can handle
    const char *success_reply_msg[3] = {CMD_READY_FOR_TRANSFER, device_id.c_str(), buf_size};
    reply_cmd(success_reply_msg, 3, cmd_msg_separator);

    state = TRANSFER_PHASE;
  } else if (state == TRANSFER_PHASE){
    if(cmd_message != "t"){
      return;
    }

    Serial.println("Command Received in Transfer Phase!");

    // Use this buffer_size for receiving data
    buffer_size = atoi(parse_cmd('\n'));

    // Does not change state here to make sure
    // This is to make sure that VERIFICATION_PHASE only starts after all data are received
  } else if (state == VERIFICATION_PHASE){
    if(cmd_message != "h"){
      return;
    }

    Serial.println("Command Received in Verification Phase!");

    // Server should have sent file's checksum
    const char* server_checksum = parse_cmd('\n');

    // Implements Update.end() partially
    // Checks  received "file"'s checksum matches with server's checksum
    bool checksum_mismatch = Update.md5String() != server_checksum;
    const char *reply_code = (checksum_mismatch) ? CMD_CHECKSUM_MISMATCH : CMD_TRANSFER_SUCCESS;
    const char *reply_msg[2] = {reply_code, device_id.c_str()};
    reply_cmd(reply_msg, 2, cmd_msg_separator);

    state = END_PHASE;
  } else if (state == END_PHASE){
    if(cmd_message != "s"){
      return;
    }

    Serial.println("Command Received in End Phase!");
    state = UPDATE_PHASE;
  }

  while (cmd_udp_context->next()){
    cmd_udp_context->flush();
  }
}

void handle_ota_service(){
  if(state == UPDATE_PHASE){
    Update.end();
  }
}

void setup() {
  Serial.begin(115200);
  Serial.println("");

  // Read config.json to initialize global variables
  bool init_params_success = init_runtime_params();
  if (!init_params_success){
    Serial.println("config.json File does not exists in SPIFFS!");
  }
  

  // Handles connecting to WiFi
  // Might loop indefinitely, indicating no respnse from SSID
  // Or no available open SSID detected
  bool gateway_wifi_connected = connect_to_wifi();


  bool init_gateway_success = init_to_gateway();
  // If successfully connected to WiFi (and Device ID Defined)
  // try to initialize to TCP Socket Server
  if(!init_params_success || !gateway_wifi_connected || !init_gateway_success){
    Serial.println("OTA Service Unavailable!");
  }

  // If successfully initialized to gateway, setup Async Multicast Listener
  if(init_gateway_success){
    set_mcast_listener(cmd_udp_context, cmd_mcast_addr, cmd_mcast_port);
    cmd_udp_context->onRx(&on_cmd_mcast_packet);
    state = STANDBY_PHASE;
    Serial.println("Starting OTA Service Listener...");
  }
}

void loop() {
  handle_ota_service();
  // put your main code here, to run repeatedly:
}
