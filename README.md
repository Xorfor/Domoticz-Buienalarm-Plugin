# Buienalarm (NL)
This Domoticz plugin retrieves data from an **undocumented** api call from https://www.buienalarm.nl/.
It seems that this api also works within other countries, but this is not implemented yet. So, this plugin currently only works within the Netherlands and the text messages are also in Dutch. 

## Installation
1. Clone repository into your Domoticz plugins folder
    ```
    cd domoticz/plugins
    git clone https://github.com/Xorfor/Domoticz-Buienalarm-Plugin.git
    ```
1. Restart domoticz
    ```
    sudo service domoticz.sh restart
    ```
1. Make sure that "Accept new Hardware Devices" is enabled in Domoticz settings
1. Go to "Hardware" page and add new hardware with Type "Buienalarm"
1. Press Add

## Update
1. Go to plugin folder and pull new version
    ```
    cd domoticz/plugins/Domoticz-Buienalarm-Plugin
    git pull
    ```
1. Restart domoticz
    ```
    sudo service domoticz.sh restart
    ```

## Parameters
None

This plugin uses the latitude and longitude as specified in Domoticz Settings -> System -> Location.

## Devices
| Name            | Description
| :---            | :---
| **Rain**        | Current percipitation
| **Text**        | Description of the rain expectations
| **Alert**       | Alert with the maximum rain rate in the coming 2 hours
| **Temperature** | Local temperature given by Buienradar

![Buienalarm](https://github.com/Xorfor/Domoticz-Buienalarm-Plugin/blob/master/buienalarm.png)

### Alert
Alerts are defined as follows:

| Level | mm/h    | Text
| ---:  | ---:    | :---
| 0     | < 0.1   | Geen neerslag
| 1     | 0.1 - 1 | Lichte neerslag
| 2     | 1 - 3   | Matige neerslag
| 3     | 3 - 10  | Zware neerslag
| 4     | > 10    | Zware buien
