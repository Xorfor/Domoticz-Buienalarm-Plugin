# Buienalarm (NL)
This Domoticz plugin retrieves data from an **undocumented** api call from https://www.buienalarm.nl/.
It seems that this api also works within other countries, but this is not implemented yet. So, this plugin currently only works within the Netherlands and the text messages are also in Dutch. 

## Parameters
None

This plugin uses the latitude and longitude as specified in Domoticz Settings -> System -> Location.

## Devices
| Name         | Description
| :---         | :---
| **Rain**     | Current percipitation
| **Text**     | Description of the rain expectations
| **Alert**    | Alert with the maximum rain rate in the coming 2 hours

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
