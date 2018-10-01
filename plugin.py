#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
<plugin key="xfr_buienalarm" name="Buienalarm" author="Xorfor" version="0.0.2" wikilink="https://github.com/Xorfor/Domoticz-Buienalarm-Plugin" externallink="https://www.buienalarm.nl/">
    <params>
        <param field="Mode6" label="Debug" width="75px">
            <options>
                <option label="True" value="Debug"/>
                <option label="False" value="Normal" default="true"/>
            </options>
        </param>
    </params>
</plugin>
"""
import Domoticz
import json
import subprocess
from datetime import datetime
from datetime import timedelta
import time


class BasePlugin:

    __PRECIP_TIME = "{:%H:%M}"

    # Next lines
    __NO_PRECIP = "Geen neerslag"
    __PRECIP = "Neerslag"
    __PRECIP_START = "Neerslag begint rond " + __PRECIP_TIME
    __PRECIP_STOP = "Neerslag stopt rond " + __PRECIP_TIME
    __PRECIP_AGAIN = " en begint weer rond " + __PRECIP_TIME
    __PRECIP_DURATION = " en duurt ongeveer tot " + __PRECIP_TIME

    __DEBUG_NONE = 0
    __DEBUG_ALL = 1

    __HEARTBEATS2MIN = 6
    __MINUTES = 1  # Data is updated every 5 minutes

    """
    Full url:
        https://cdn-secure.buienalarm.nl/api/3.4/forecast.php?lat={}&lon={}&region=nl&unit=mm/u
    """
    __API_DOMAIN = "https://cdn-secure.buienalarm.nl/api/"
    __API_VERSION = "3.4"
    __API_PARAMETERS = "/forecast.php?lat={}&lon={}&region={}&unit=mm/u"
    #
    __API_URL = __API_DOMAIN + __API_VERSION + __API_PARAMETERS
    # __API_HEADER = ""

    # Device units
    __UNIT_RAIN = 1
    __UNIT_TEXT = 2
    __UNIT_ALERT = 3

    __UNITS = [
        # Unit, Name, Type, Subtype, Options, Used
        [__UNIT_ALERT, "Alert", 243, 22, {}, 1],
        [__UNIT_RAIN, "Rain", 85, 1, {"0;0"}, 1],
        [__UNIT_TEXT, "Text", 243, 19, {}, 1],
    ]

    def __init__(self):
        self.__runAgain = 0

    def onStart(self):
        Domoticz.Log("onStart")
        # Set Debug mode
        if Parameters["Mode6"] == "Debug":
            Domoticz.Debugging(self.__DEBUG_ALL)
        else:
            Domoticz.Debugging(self.__DEBUG_NONE)
        self.__region = "nl"
        # Get Domoticz location
        loc = Settings["Location"].split(";")
        self.__lat = float(loc[0])
        self.__lon = float(loc[1])
        if self.__lat is None or self.__lon is None:
            Domoticz.Error("Unable to parse coordinates")
            return False
        # Create devices
        if len(Devices) == 0:
            # Following devices are set on used by default
            for unit in self.__UNITS:
                Domoticz.Device(Unit=unit[0],
                                Name=unit[1],
                                Type=unit[2],
                                Subtype=unit[3],
                                Options=unit[4],
                                Used=unit[5]).Create()
        DumpAllToLog()

    def onStop(self):
        Domoticz.Debug("onStop")

    def onConnect(self, Connection, Status, Description):
        Domoticz.Debug("onConnect: " + Connection.name +
                       " - " + str(Status) + " - " + Description)

    def onMessage(self, Connection, Data):
        Domoticz.Debug("onMessage: " + Connection.name)

    def onCommand(self, Unit, Command, Level, Hue):
        Domoticz.Debug("onCommand: " + str(Unit) + ": Parameter '" +
                       str(Command) + "', Level: " + str(Level))

    def onNotification(self, Name, Subject, Text, Status, Priority, Sound, ImageFile):
        Domoticz.Debug("onNotification: " + Name + "," + Subject + "," + Text + "," + Status + "," + str(
            Priority) + "," + Sound + "," + ImageFile)

    def onDisconnect(self, Connection):
        Domoticz.Debug("onDisconnect: " + Connection.name)

    def onHeartbeat(self):
        self.__runAgain -= 1
        if self.__runAgain <= 0:
            self.__runAgain = self.__HEARTBEATS2MIN * self.__MINUTES
            if self.__region is None:
                # Get region
                # To get region (country/identifier or country/countryCode):
                # https://nominatim.openstreetmap.org/reverse?format=json&lat={}&lon={}&zoom=18&addressdetails=1
                # Prepare url to get data
                # New York: 40.71427, -74.00597
                # Lausanne, Switcherland: 46.51965,6.63227
                # self.__lat = 46.51965
                # self.__lon = 6.63227
                # values = getData("https://nominatim.openstreetmap.org/reverse?format=json&lat={}&lon={}&zoom=18&addressdetails=1".format(self.__lat, self.__lon))
                # self.__region = values.get("address").get("country_code")
                # Domoticz.Debug("region: {}".format(self.__region))
                pass
            else:
                # Get rain data
                # Domoticz.Error("region: {}".format(self.__region))
                values = getData(self.__API_URL.format(
                    self.__lat, self.__lon, self.__region))
                # Domoticz.Debug("values: " + str(values))
                # Domoticz.Debug("success: " + str(values.get("success")))
                if values.get("success", False):
                    t = values.get("start_human")
                    # Domoticz.Debug("t: " + t)
                    now = datetime.now()
                    startData = now.strftime("%Y-%m-%d") + " " + t
                    # Avoid bug in Python
                    try:
                        brDT = datetime.strptime(startData, "%Y-%m-%d %H:%M")
                    except TypeError:
                        brDT = datetime(
                            *(time.strptime(startData, "%Y-%m-%d %H:%M")[0:6]))
                    # Domoticz.Debug("brDT: " + str(brDT))
                    precip = values.get("precip", [])
                    Domoticz.Debug("precip: " + str(precip))
                    #
                    # Create text describing the expected precipitation
                    raining = 0
                    maxP = 0
                    maxDT = None
                    status = ""
                    i = 0
                    j = 0
                    # Loop through the precipitation list. One value each 5 minutes
                    for p in precip:
                        dt = brDT + timedelta(minutes=i * 5)
                        i += 1
                        # We are sometimes also getting 'old' data. Skip this!
                        if dt >= now:
                            j += 1
                            # Domoticz.Debug("{}: {}".format(dt, p))
                            """
                            0: Geen neerslag
                            1: Neerslag
                            2: Neerslag stopt rond {}
                            3: Neerslag stopt rond {} <+> en begint weer rond {}
                            4: Neerslag begint rond {}
                            5: Neerslag begint rond {} <+> en duurt ongeveer tot {}
                            """
                            if j == 1:
                                if p == 0:
                                    # Currently no rain
                                    raining = 0
                                    status = self.__NO_PRECIP
                                else:
                                    # It is raining now
                                    raining = 1
                                    status = self.__PRECIP
                                # Display current rain
                                UpdateDevice(self.__UNIT_RAIN, 0,
                                             "{};{}".format(100*p, 0))
                            else:
                                if raining == 0:
                                    if p > 0:
                                        # Rain starts within 2 hours
                                        raining = 4
                                        # start = dt
                                        status = self.__PRECIP_START.format(dt)
                                elif raining == 1:
                                    if p == 0:
                                        # It is currently raining but will stop within 2 hours
                                        raining = 2
                                        # end = dt
                                        status = self.__PRECIP_STOP.format(dt)
                                elif raining == 2:
                                    if p > 0:
                                        # Raining will stop but restart within 2 hours
                                        raining = 3
                                        # start = dt
                                        status += self.__PRECIP_AGAIN.format(
                                            dt)
                                elif raining == 4:
                                    if p == 0:
                                        # Rain starts within 2 hours but will stop
                                        raining = 5
                                        # end = dt
                                        status += self.__PRECIP_DURATION.format(
                                            dt)
                            if p > maxP:
                                maxP = p
                                maxDT = dt
                        else:
                            pass
                            # Domoticz.Debug("Now: {}".format(now))
                            # Domoticz.Debug("startData: {}".format(startData))
                    # Looped through precipitation, so update device
                    UpdateDevice(self.__UNIT_TEXT, 0, status)
                    """
                    Precipitation Alert:

                    zware buien > 10
                    zware neerslag 3-10 mm
                    matige neerslag 1-3 mm
                    lichte neerslag 0.1-1 mm
                    geen neerslag 0 mm
                    """
                    maxP = round(maxP, 1)
                    if maxP < 0.1:
                        alertLevel = 0
                        alertText = "Geen neerslag"
                    elif maxP <= 1:
                        alertLevel = 1
                        alertText = "Lichte neerslag ({} mm/h @ {:%H:%M})".format(
                            maxP, maxDT)
                    elif maxP <= 3:
                        alertLevel = 2
                        alertText = "Matige neerslag ({} mm/h @ {:%H:%M})".format(
                            maxP, maxDT)
                    elif maxP <= 10:
                        alertLevel = 3
                        alertText = "Zware neerslag ({} mm/h @ {:%H:%M})".format(
                            maxP, maxDT)
                    elif maxP > 10:
                        alertLevel = 4
                        alertText = "Zware buien ({} mm/h @ {:%H:%M})".format(
                            maxP, maxDT)
                    UpdateDevice(self.__UNIT_ALERT, alertLevel, alertText)

                    Domoticz.Debug("# datapoints: {}/{}".format(j, i))
                else:
                    Domoticz.Debug("No data received")


global _plugin
_plugin = BasePlugin()


def onStart():
    global _plugin
    _plugin.onStart()


def onStop():
    global _plugin
    _plugin.onStop()


def onConnect(Connection, Status, Description):
    global _plugin
    _plugin.onConnect(Connection, Status, Description)


def onMessage(Connection, Data):
    global _plugin
    _plugin.onMessage(Connection, Data)


def onCommand(Unit, Command, Level, Hue):
    global _plugin
    _plugin.onCommand(Unit, Command, Level, Hue)


def onNotification(Name, Subject, Text, Status, Priority, Sound, ImageFile):
    global _plugin
    _plugin.onNotification(Name, Subject, Text, Status,
                           Priority, Sound, ImageFile)


def onDisconnect(Connection):
    global _plugin
    _plugin.onDisconnect(Connection)


def onHeartbeat():
    global _plugin
    _plugin.onHeartbeat()


################################################################################
# Get data
################################################################################
def getData(url):
    command = "curl -X GET "
    options = "'" + url + "'"
    Domoticz.Debug(command + " " + options)
    p = subprocess.Popen(command + " " + options,
                         shell=True, stdout=subprocess.PIPE)
    p.wait()
    data, errors = p.communicate()
    if p.returncode != 0:
        Domoticz.Error("Request failed")
        values = {}
    else:
        values = json.loads(data.decode("utf-8"))
    return values


# Vervallen?
def value2mmph(value):
    if value > 0:
        return round(10 ** ((value - 109) / 32), 1)
    else:
        return 0

################################################################################
# Generic helper functions
################################################################################


def DumpDevicesToLog():
    # Show devices
    Domoticz.Debug("Device count.........: " + str(len(Devices)))
    for x in Devices:
        Domoticz.Debug("Device...............: " +
                       str(x) + " - " + str(Devices[x]))
        Domoticz.Debug("Device Idx...........: " + str(Devices[x].ID))
        Domoticz.Debug("Device Type..........: " +
                       str(Devices[x].Type) + " / " + str(Devices[x].SubType))
        Domoticz.Debug("Device Name..........: '" + Devices[x].Name + "'")
        Domoticz.Debug("Device nValue........: " + str(Devices[x].nValue))
        Domoticz.Debug("Device sValue........: '" + Devices[x].sValue + "'")
        Domoticz.Debug("Device Options.......: '" +
                       str(Devices[x].Options) + "'")
        Domoticz.Debug("Device Used..........: " + str(Devices[x].Used))
        Domoticz.Debug("Device ID............: '" +
                       str(Devices[x].DeviceID) + "'")
        Domoticz.Debug("Device LastLevel.....: " + str(Devices[x].LastLevel))
        Domoticz.Debug("Device Image.........: " + str(Devices[x].Image))


def DumpImagesToLog():
    # Show images
    Domoticz.Debug("Image count..........: " + str(len(Images)))
    for x in Images:
        Domoticz.Debug("Image '" + x + "...': '" + str(Images[x]) + "'")


def DumpParametersToLog():
    # Show parameters
    Domoticz.Debug("Parameters count.....: " + str(len(Parameters)))
    for x in Parameters:
        if Parameters[x] != "":
            Domoticz.Debug("Parameter '" + x + "'...: '" +
                           str(Parameters[x]) + "'")


def DumpSettingsToLog():
    # Show settings
    Domoticz.Debug("Settings count.......: " + str(len(Settings)))
    for x in Settings:
        Domoticz.Debug("Setting '" + x + "'...: '" + str(Settings[x]) + "'")


def DumpAllToLog():
    DumpDevicesToLog()
    DumpImagesToLog()
    DumpParametersToLog()
    DumpSettingsToLog()


def DumpHTTPResponseToLog(httpDict):
    if isinstance(httpDict, dict):
        Domoticz.Debug("HTTP Details (" + str(len(httpDict)) + "):")
        for x in httpDict:
            if isinstance(httpDict[x], dict):
                Domoticz.Debug(
                    "....'" + x + " (" + str(len(httpDict[x])) + "):")
                for y in httpDict[x]:
                    Domoticz.Debug("........'" + y + "':'" +
                                   str(httpDict[x][y]) + "'")
            else:
                Domoticz.Debug("....'" + x + "':'" + str(httpDict[x]) + "'")


def UpdateDevice(Unit, nValue, sValue, TimedOut=0, AlwaysUpdate=False):
    if Unit in Devices:
        if Devices[Unit].nValue != nValue \
                or Devices[Unit].sValue != sValue \
                or Devices[Unit].TimedOut != TimedOut \
                or AlwaysUpdate:
            Devices[Unit].Update(
                nValue=nValue, sValue=str(sValue), TimedOut=TimedOut)
            Domoticz.Debug(
                "Device update " + Devices[Unit].Name + ": " + str(nValue) + " - '" + str(sValue) + "'")


def UpdateDeviceOptions(Unit, Options={}):
    if Unit in Devices:
        if Devices[Unit].Options != Options:
            Devices[Unit].Update(nValue=Devices[Unit].nValue,
                                 sValue=Devices[Unit].sValue, Options=Options)
            Domoticz.Debug("Device Options update: " +
                           Devices[Unit].Name + " = " + str(Options))


def UpdateDeviceImage(Unit, Image):
    if Unit in Devices and Image in Images:
        if Devices[Unit].Image != Images[Image].ID:
            Devices[Unit].Update(nValue=Devices[Unit].nValue,
                                 sValue=Devices[Unit].sValue, Image=Images[Image].ID)
            Domoticz.Debug("Device Image update: " +
                           Devices[Unit].Name + " = " + str(Images[Image].ID))
