# FlClash 与 Stash 共同分流

同一套用途分组、规则顺序与固定规则快照，生成两份客户端配置。日常国内用途默认 **直连**，境外用途默认 **全球加速**；地区内自动测速，不需要逐个服务选择节点。

## 文件与使用

- `flclash.yaml`：FlClash/Mihomo 完整配置。
- `stash.yaml`：Stash iOS 完整配置。
- `shared/`：共同分组、分流顺序、自有补充、订阅示例。
- `templates/`：各客户端的运行设置；不是可以互相复制的万能 YAML。
- `vendor/`：上游规则原文、MIT 许可和带提交/hash 的清单。
- `rules/sha256/`：按服务分类和内容哈希命名的共享规则文件（域名与 IP 分类分开），更新时保留旧版本；配置中的 provider 标识对应分类，例如 `google-domain`、`china-ipcidr`，重点 DNS 使用 `proxy-dns`。
- `excluded-rules.json`：被排除的不通用上游表达式，不能误称完整移植。
- `stash/overrides/`：[B 站、微信外链、小红书三个独立可选覆写](stash/overrides/README.md)，需单独导入和本机 CA；主配置不自动启用。

**两个订阅地址都是不可用的 `.invalid` 示例，配置不是开箱即用的代理服务。**

可以下载完整 YAML，直接在客户端本地编辑 `proxy-providers` 的 URL，再导入使用。两个 provider 互相独立，支持各自更新；只需一个时，删除第二个 provider 和各组 `use` 中的对应引用。订阅应提供兼容的节点列表，不能把 QX 原文直接当作节点订阅。

若在电脑上生成私有版本：

```sh
python -m venv .venv
. .venv/bin/activate
python -m pip install -r clash/requirements.txt
cp clash/shared/subscriptions.example.yaml clash/shared/subscriptions.local.yaml
# 在 local 文件中填写真实订阅，不要编辑已提交的 example 文件。
python clash/scripts/config.py --subscriptions clash/shared/subscriptions.local.yaml --output-dir clash/local
```

导入 `clash/local/flclash.yaml` 或 `clash/local/stash.yaml`。`local/` 和私有订阅文件已经 gitignore；它们仍包含秘密，分享或提交前请再次检查。不要将个人订阅作为公开 GitHub 配置地址发布。

## 分组

- **全球加速**：新加坡、日本、台湾、美国、香港、直连、自动选择、手动选择。首次默认新加坡。
- **兜底分流及境外用途**：全球加速、直连、新加坡、日本、台湾、美国、香港。
- **国内用途**：同一候选集合，但把直连放第一项，确保两个客户端首次导入的默认行为一致。客户端已保存的手动选择可能优先于配置顺序。
- 五个地区组直接用 `url-test`，按节点名称筛选；自动选择涵盖所有订阅节点，不含直连。默认每 600 秒测试，容差 50ms，避免微小延迟差导致频繁换 IP。可在 `shared/groups.yaml` 调整。
- 地区名、国旗和常用缩写通过正则匹配，不能判断供应商真实出口；节点名称不规范时需调整过滤式。
- 测速使用 IP 地址形式的 Cloudflare HTTPS 端点，避免选择代理时先依赖境外 DNS；只代表该地址连通性/延迟，不代表吞吐量、解锁或目标服务可用性。

五个地区组不包含额外的 `REJECT` 候选，只展示匹配地区的订阅节点。地区没有匹配节点时，空组行为由客户端决定；**Stash 实机尚未验证，初次导入应检查实际表现**。涵盖全部节点的“自动选择”和“手动选择”仍保留 `REJECT`，手动组主动选择实际节点后才可用。

## 分流与覆盖范围

微信、哔哩哔哩、苹果服务、国内服务默认直连；AI、GitHub、加密货币、Google、YouTube、Telegram、Microsoft、Spotify、国际媒体、游戏服务默认全球加速。具体服务优先于宽泛厂商规则，例如 AI/Gemini/Copilot 先于 Google/GitHub，YouTube 先于 Google。国内域名与固定中国 IP 段位于具体服务之后；未分类目的地由兜底处理。

微信使用精简的专有域名补充，不把所有 `qq.com` 或共享 CDN 当成微信。中国域名覆盖来自 `cn` 集合，并非“所有中国应用”的完备证明。国内下载/CDN 在厂商分类内可能仍走其用途组，可按需要在 `shared/rules/local.yaml` 加精确例外。

上游来自 v2fly/domain-list-community 和 gaoyifan/china-operator-ip；原文保持固定提交，MIT 通知随仓库保留。国际媒体首版覆盖 Netflix、Disney、HBO、Prime Video、Twitch。第一版不叠加广告拦截大库。仅采用共同的域名/IP规则，不采用 PROCESS-NAME、ASN、GEOIP、GEOSITE 或 MRS，避免平台语义差异和隐式数据库下载。不能通用的正则规则写入排除报告，对应请求仍按后续分类/兜底处理。

路由与 DNS 域名清单分别保存在 `rules/sha256/` 中，两个入口文件引用本仓库 main 上的具体内容哈希文件，首启会从 GitHub 下载；并非内联。配置生成时校验文件名与内容哈希、拒绝同名覆盖，更新只新增文件并保留旧文件；文件内容和文件名由 CI 校验，保留旧文件仍依赖仓库维护约定；**客户端不会自行校验哈希**。主分支链接只有 PR 合并后才能取到新文件；更新内容要审查 PR。订阅更新与规则更新分开。Mihomo v1.19.33 本地测试发现：首次无缓存且下载失败时核心仍启动，但规则集合为空，流量会按其余规则/兜底处理；不能假设自动停止或安全降级。已有缓存离线重启可用。Stash 下载失败及缓存行为尚未实测。首次导入可以先使用客户端全局模式完成下载，确认所有规则集均已下载且条目数非零，再切回规则模式；全局模式本身不保证所有 DNS 查询都经过代理。如果当前网络不能直接访问 GitHub 原始文件，首次获取可能失败，需先解决连接或用可信方式预置规则缓存；不能假设已有代理节点足以解决冷启动。

## DNS 策略与边界

两端对 Google、YouTube、AI、GitHub、加密货币和 Telegram 的重点域名使用 Cloudflare DoH（1.1.1.1）经仅含代理节点的“自动选择”组，当前共有 1,607 条去重匹配；其余域名（包括未分类的境外域名）默认使用阿里/腾讯 DoH。此清单不可能涵盖全部被污染、敏感或检测 DNS 的域名，未知境外域名可能交给国内 DNS；需要时在共享规则扩充。例如 google.cn 属于 Google 集合，将使用境外 DNS，即使具体用途可能希望直连；可按需调整分类。境外指定 DNS 无国内服务器回退，但规则文件缺失时策略不生效，会用默认国内 DNS，详见首次下载风险。客户端缓存可能短期保留旧结果。实际服务路由可手动切换，DNS 分类不会随分组切换同步。

代理节点的域名通过独立的国内 DoH 解析以避免依赖循环；订阅 URL 主机名和 raw.githubusercontent.com 为启动下载规则/订阅显式采用国内 DoH，也属于国外解析例外。DoH 服务器域名仍由 223.5.5.5/119.29.29.29 引导，这些引导查询未加密且属于披露的例外。`.local`、`.lan`、`.localhost` 和部分私有 IPv4 反向查询使用系统 DNS 以便本地发现，其内容可能交给当前网络的 DNS。DNS 服务商能看到其接收到的查询。

Stash 使用 Fake-IP，启用 follow-rule 将境外 DoH 出站交给代理，并保留国内 DoH 直连。DNS 分类只包含重点境外域名，不等于业务分流规则；实际表现需分别实测。需要 iOS 版 Stash 3.6 或以上支持独立代理节点 DNS；版本及实际行为未在真机验证。为避免循环，两端规则将全部目的地为 1.1.1.1/32 的连接交给自动代理，不仅仅影响 DNS。空节点防直连在 Mihomo 模拟验证通过，Stash 仍需真机验证。域名策略和分流规则采用 domain/ipcidr 规则集，但 Stash 的启动耗时、DNS 匹配和内存影响尚未测量。

FlClash 保持 redir-host，TUN 默认关闭，由用户在客户端决定；开启 TUN 才有可能覆盖更多非系统代理应用。应用自带 DoH、系统 DNS、LAN DNS、浏览器安全 DNS、VPN 中断、休眠/网络切换和 IPv6 都需要单独实测。**这不是完全防 DNS 泄漏的保证。** FlClash 默认开启 IPv6 及 DNS IPv6 解析；Stash 的 IPv6 仍默认关闭，客户端覆写可能改变行为。

不启用控制接口、面板或局域网代理共享。FlClash 管理内核所必需的本机通信由应用控制，不属于这份配置对外开放的 API。

## 审查后更新上游

先选择并审查上游明确提交，再运行（必须是完整 40 位 commit，不接受浮动分支）：

```sh
python clash/scripts/update_vendor.py \
  --domain-revision <v2fly-commit> \
  --ip-revision <china-operator-ip-commit>
python clash/scripts/config.py
python -m unittest discover -s clash/tests -v
git diff --stat
git diff -- clash/vendor/manifest.json clash/excluded-rules.json
# 审查原文、规则和生成配置差异后，再由人决定 commit / PR。
```

更新工具只修改工作区，不提交、不推送、不操作用户订阅；新许可内容发生变化会停止。常规生成/测试完全使用仓库内快照，不联网更新规则。

## 验证

```sh
python clash/scripts/config.py --check
python -m unittest discover -s clash/tests -v
python clash/scripts/check_mihomo.py /path/to/mihomo
python clash/scripts/check_selection.py /path/to/mihomo
python clash/scripts/check_rule_providers.py /path/to/mihomo
```

单测覆盖重复键、上游 hash、生成一致性、引用/环、两端路由等价、分组默认值、地区筛选、分类样例、属性 include 和私有输出保护。Mihomo 检查使用合成的本地订阅，无真实账号或公网代理。选择测试只在临时进程上打开带测试口令的 `127.0.0.1` 控制接口，测试后关闭，**不会写入交付配置**。

CI 下载固定版本和校验值的官方 Mihomo，验证规则文件及回环测试；真实 GitHub 首启下载仍需在合并后验证。未覆盖 FlClash UI、Stash 真机、真实订阅协议、实际 DNS/网络出口；通过 CI 不代表这些已验收。首次使用请分别测试微信、B站、AI、GitHub、YouTube 等，并在客户端连接日志核对命中组。

## 设计参考

- [用户原 QX 模板](https://ddgksf2013.top/Profile/QuantumultX.conf)：参考用途组/地区组结构，不复制脚本或安全弱化设置。
- [Repcz Mihomo](https://github.com/Repcz/Tool/blob/X/mihomo/Client/config.yaml) 与 [Stash](https://github.com/Repcz/Tool/blob/X/Stash/Stash.yaml)：参考组织方式；配置为独立实现。
- [Mihomo 代理集合](https://wiki.metacubex.one/config/proxy-providers/)；[Stash 代理集合](https://stash.wiki/proxy-protocols/proxy-providers)；[Stash 策略组](https://stash.wiki/proxy-protocols/proxy-groups)。
