# WiFU - Advanced WiFi Penetration Toolkit

<p align="center">
    <a href="https://github.com/ItachiOwO/WIFU/releases/latest"><img alt="Release" src="https://img.shields.io/github/v/release/ItachiOwO/WIFU?style=flat-square&color=blue"></a>
    <a href="https://github.com/ItachiOwO/WIFU/blob/master/LICENSE.md"><img alt="Software License" src="https://img.shields.io/badge/license-GPL3-brightgreen.svg?style=flat-square"></a>
    <a href="https://github.com/ItachiOwO/WIFU/stargazers"><img alt="Stars" src="https://img.shields.io/github/stars/ItachiOwO/WIFU?style=flat-square&color=yellow"></a>
    <a href="https://github.com/ItachiOwO/WIFU/network/members"><img alt="Forks" src="https://img.shields.io/github/forks/ItachiOwO/WIFU?style=flat-square&color=orange"></a>
</p>

<p align="center">
    <b>WiFU is an advanced AI-powered toolkit for WiFi security analysis and penetration testing.</b>
</p>

## 🌟 Features

WiFU combines **AI-driven learning** with **direct attack capabilities** to create a comprehensive WiFi security toolkit:

### 🤖 AI-Powered Learning System
- **Deep Reinforcement Learning** (A2C) algorithms that optimize attack strategies
- **Adaptive Parameters** that learn from your environment
- **Automatic Optimization** of channel hopping, deauthentication timing, and target selection
- **Multi-device Cooperation** between WiFU units for optimal channel coverage

### ⚔️ Direct Attack Capabilities
- **WPA2 Handshake Capture** - Efficient 4-way handshake collection
- **PMKID Extraction** - Client-less attack against access points
- **WPA3 Downgrade Attack** - Force transition mode on WPA3 networks
- **Evil Twin Deployment** - Create convincing rogue access points
- **Dragonblood Exploitation** - Target vulnerabilities in WPA3's SAE implementation

## 📱 Interactive UI

WiFU features a personality-driven interface that gives feedback on its learning progress.

The UI provides real-time feedback on:
- Current epoch and learning state
- Number of access points and clients detected
- Handshakes captured
- Current channel and optimization strategies

## 🚀 Getting Started

### Installation

```bash
# Clone the repository
git clone https://github.com/ItachiOwO/WIFU.git
cd WIFU

# Install dependencies
pip install -r requirements.txt

# Run WiFU
sudo ./bin/wifu
```

### Attack Mode

WiFU's interactive attack mode provides a menu-driven interface to launch specialized attacks:

```bash
sudo ./bin/wifu --attack-mode
```

Select from multiple attack options and provide your wireless interface to begin targeted testing.

### Manual Mode

For direct control without AI learning:

```bash
sudo ./bin/wifu --manual
```

## 🔍 How It Works

WiFU uses an [LSTM with MLP feature extractor](https://stable-baselines.readthedocs.io/en/master/modules/policies.html#stable_baselines.common.policies.MlpLstmPolicy) as its policy network for the [A2C agent](https://stable-baselines.readthedocs.io/en/master/modules/a2c.html). 

The learning process involves:
1. **Observation** of the WiFi environment
2. **Parameter optimization** for maximum handshake capture
3. **Adaptive strategies** based on network density and activity
4. **Continuous improvement** through reinforcement learning

## ⚠️ Legal Disclaimer

**WiFU is for authorized penetration testing and security research only.** 

Unauthorized use against networks you don't own or have explicit permission to test is illegal and may result in criminal charges. Users are solely responsible for ensuring all testing complies with local, state, and federal laws. The developers assume no liability for misuse or damage caused by this program.

## 📚 Documentation

For comprehensive documentation, visit our wiki: [WiFU Documentation](https://github.com/ItachiOwO/WIFU/wiki)

## 🔄 Updates & Contributions

WiFU is actively maintained and welcomes contributions:

- **Report bugs** by opening issues
- **Suggest features** through pull requests
- **Improve documentation** to help new users

## 📄 License

WiFU is released under the [GPL3 License](LICENSE.md).

# WiFU: WPA2/WPA3 Attack Toolkit

[WiFU](https://wifu.ai/) is an [A2C](https://hackernoon.com/intuitive-rl-intro-to-advantage-actor-critic-a2c-4ff545978752)-based "AI" leveraging [bettercap](https://www.bettercap.org/) that learns from its surrounding WiFi environment to maximize the crackable WPA key material it captures (either passively, or by performing authentication and association attacks). This material is collected as PCAP files containing any form of handshake supported by [hashcat](https://hashcat.net/hashcat/), including [PMKIDs](https://www.evilsocket.net/2019/02/13/Pwning-WiFi-networks-with-bettercap-and-the-PMKID-client-less-attack/), 
full and half WPA handshakes.

Instead of merely playing [Super Mario or Atari games](https://becominghuman.ai/getting-mario-back-into-the-gym-setting-up-super-mario-bros-in-openais-gym-8e39a96c1e41?gi=c4b66c3d5ced) like most reinforcement learning-based "AI" *(yawn)*, WiFU tunes [its parameters](https://github.com/ItachiOwO/WIFU/blob/master/wifu/defaults.toml) over time to **get better at pwning WiFi things** in the environments you expose it to. 

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
./bin/wifu --attack-mode
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
