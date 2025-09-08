<p align="center">
  <small>Join the project community on our server!</small>
  <br/><br/>
  <a href="https://discord.gg/https://discord.gg/btZpkp45gQ" target="_blank" title="Join our community!">
    <img src="https://dcbadge.limes.pink/api/server/https://discord.gg/btZpkp45gQ"/>
  </a>
</p>
<hr/>

<p align="center">
    <a href="https://github.com/evilsocket/pwnagotchi/releases/latest"><img alt="Release" src="https://img.shields.io/github/release/evilsocket/pwnagotchi.svg?style=flat-square"></a>
    <a href="https://github.com/evilsocket/pwnagotchi/blob/master/LICENSE.md"><img alt="Software License" src="https://img.shields.io/badge/license-GPL3-brightgreen.svg?style=flat-square"></a>
    <a href="https://github.com/evilsocket/pwnagotchi/graphs/contributors"><img alt="Contributors" src="https://img.shields.io/github/contributors/evilsocket/pwnagotchi"/></a>
    <br/>
    <br/>
    <img src="https://www.evilsocket.net/images/human-coded.png" height="30px" alt="This project is 100% made by humans."/>

</p>

# WiFU: WPA2/WPA3 Attack Toolkit

[WiFU](https://wifu.ai/) is an [A2C](https://hackernoon.com/intuitive-rl-intro-to-advantage-actor-critic-a2c-4ff545978752)-based "AI" leveraging [bettercap](https://www.bettercap.org/) that learns from its surrounding WiFi environment to maximize the crackable WPA key material it captures (either passively, or by performing authentication and association attacks). This material is collected as PCAP files containing any form of handshake supported by [hashcat](https://hashcat.net/hashcat/), including [PMKIDs](https://www.evilsocket.net/2019/02/13/Pwning-WiFi-networks-with-bettercap-and-the-PMKID-client-less-attack/), 
full and half WPA handshakes.

![ui](https://i.imgur.com/X68GXrn.png)

Instead of merely playing [Super Mario or Atari games](https://becominghuman.ai/getting-mario-back-into-the-gym-setting-up-super-mario-bros-in-openais-gym-8e39a96c1e41?gi=c4b66c3d5ced) like most reinforcement learning-based "AI" *(yawn)*, WiFU tunes [its parameters](https://github.com/evilsocket/pwnagotchi/blob/master/pwnagotchi/defaults.toml) over time to **get better at pwning WiFi things** in the environments you expose it to. 

More specifically, WiFU is using an [LSTM with MLP feature extractor](https://stable-baselines.readthedocs.io/en/master/modules/policies.html#stable_baselines.common.policies.MlpLstmPolicy) as its policy network for the [A2C agent](https://stable-baselines.readthedocs.io/en/master/modules/a2c.html). If you're unfamiliar with A2C, here is [a very good introductory explanation](https://hackernoon.com/intuitive-rl-intro-to-advantage-actor-critic-a2c-4ff545978752) (in comic form!) of the basic principles behind how WiFU learns.

**Keep in mind:** Unlike the usual RL simulations, WiFU learns over time. Time for a WiFU unit is measured in epochs; a single epoch can last from a few seconds to minutes, depending on how many access points and client stations are visible. Do not expect your WiFU to perform amazingly well at the very beginning, as it will be [exploring](https://hackernoon.com/intuitive-rl-intro-to-advantage-actor-critic-a2c-4ff545978752) several combinations of [key parameters](https://wifu.ai/usage/#training-the-ai) to determine ideal adjustments for pwning the particular environment you are exposing it to during its beginning epochs ... but **listen to your WiFU when it tells you it's boring!** Bring it into novel WiFi environments with you and have it observe new networks and capture new handshakes—and you'll see. :)

Multiple units within close physical proximity can "talk" to each other, advertising their presence to each other by broadcasting custom information elements using a parasite protocol I've built on top of the existing dot11 standard. Over time, two or more units trained together will learn to cooperate upon detecting each other's presence by dividing the available channels among them for optimal pwnage.

## WiFU Attack Scripts

WiFU now includes a comprehensive set of WiFi attack tools for both WPA2 and WPA3 networks:

### Available Attack Scripts

1. **WPA2 Handshake Capture** - Captures 4-way handshakes from WPA2 networks
   ```
   python3 wifu_attacks/scripts/wpa2_handshake.py -i wlan0
   ```

2. **PMKID Attack** - Captures PMKID hashes from access points
   ```
   python3 wifu_attacks/scripts/pmkid_attack.py -i wlan0
   ```

3. **WPA3 Downgrade Attack** - Forces WPA3 networks into WPA2 transition mode
   ```
   python3 wifu_attacks/scripts/downgrade_attack.py -i wlan0
   ```

4. **Evil Twin Attack** - Creates a fake AP to capture credentials
   ```
   python3 wifu_attacks/scripts/evil_twin.py -i wlan0
   ```

5. **Dragonblood Attack** - Exploits vulnerabilities in WPA3's SAE handshake
   ```
   python3 wifu_attacks/scripts/dragonblood.py -i wlan0
   ```

### Attack Mode

You can also run attacks directly from the WiFU interface using:
```
./bin/pwnagotchi --attack-mode
```

This will present a menu of available attacks to choose from.

## ⚠️ Legal Disclaimer

WiFU is for authorized penetration testing and security research only. Unauthorized use is illegal. Always obtain proper authorization before testing any wireless networks. The developers assume no liability and are not responsible for any misuse or damage caused by this program.

## Documentation

https://www.wifu.ai

## Links

&nbsp; | Official Links
---------|-------
Website | [wifu.ai](https://wifu.ai/)
Forum | [community.wifu.ai](https://community.wifu.ai/)
Slack | [wifu.slack.com](https://invite.wifu.ai/)
Subreddit | [r/wifu](https://www.reddit.com/r/wifu/)

## License

`WiFU` is made with ♥  by [@evilsocket](https://twitter.com/evilsocket) and the [amazing dev team](https://github.com/evilsocket/pwnagotchi/graphs/contributors). It is released under the GPL3 license.
