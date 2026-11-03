# FlClash 与 Stash 共同分流

同一套用途分组、规则顺序与固定规则快照，生成两份客户端配置。日常国内用途默认 **直连**，境外用途默认 **全球加速**；地区内自动测速，不需要逐个服务选择节点。

## 文件与使用

- `flclash.yaml`：FlClash/Mihomo 完整配置。
- `stash.yaml`：Stash iOS 完整配置。
- `shared/`：共同分组、分流顺序、自有补充、订阅示例。
- `templates/`：各客户端的运行设置；不是可以互相复制的万能 YAML。
- `vendor/`：上游规则原文、MIT 许可和带提交/hash 的清单。
- `excluded-rules.json`：被排除的不通用上游表达式，不能误称完整移植。
- `stash/overrides/`：预留独立的 MITM/脚本扩展，第一版不启用。

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
- 测速只代表测试地址连通性/延迟，不代表吞吐量、解锁或目标服务可用性。

各自动组额外保留 `REJECT` 作为无节点保护，它不应通过健康检查。否则 Stash 的空组会自动变成直连。Mihomo 的正常/空订阅行为有本地合成测试；**Stash 实机尚未验证，初次导入必须检查无节点地区不走直连**。手动选择初始为 REJECT，主动选择实际节点后才可用，避免订阅失败时无意直连。

## 分流与覆盖范围

微信、哔哩哔哩、苹果服务、国内服务默认直连；AI、GitHub、加密货币、Google、YouTube、Telegram、Microsoft、Spotify、国际媒体、游戏服务默认全球加速。具体服务优先于宽泛厂商规则，例如 AI/Gemini/Copilot 先于 Google/GitHub，YouTube 先于 Google。国内域名与固定中国 IP 段位于具体服务之后；未分类目的地由兜底处理。

微信使用精简的专有域名补充，不把所有 `qq.com` 或共享 CDN 当成微信。中国域名覆盖来自 `cn` 集合，并非“所有中国应用”的完备证明。国内下载/CDN 在厂商分类内可能仍走其用途组，可按需要在 `shared/rules/local.yaml` 加精确例外。

上游来自 v2fly/domain-list-community 和 gaoyifan/china-operator-ip；原文保持固定提交，MIT 通知随仓库保留。国际媒体首版覆盖 Netflix、Disney、HBO、Prime Video、Twitch。第一版不叠加广告拦截大库。仅采用共同的域名/IP规则，不采用 PROCESS-NAME、ASN、GEOIP、GEOSITE 或 MRS，避免平台语义差异和隐式数据库下载。不能通用的正则规则写入排除报告，对应请求仍按后续分类/兜底处理。

**所有运行时规则已展开在配置内**，没有客户端访问上游规则 URL 的步骤。订阅更新与规则更新分开。DNS 服务、测速地址及节点订阅属于网络服务，不是自动更新的规则文件。

DNS 使用明确列出的阿里/腾讯 DoH 与引导 DNS，便于国内使用；不宣称匿名或完全防 DNS 泄露，解析服务仍能看到查询。FlClash 使用 redir-host，TUN 由客户端控制；Stash 使用自身 iOS 网络栈。IPv6 默认关闭，仍保留私网/国内 IPv6 匹配以防客户端覆写。导入后需核对客户端 DNS/TUN 覆写，不能把“规则相同”理解为两端网络栈完全相同。

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
```

单测覆盖重复键、上游 hash、生成一致性、引用/环、两端路由等价、分组默认值、地区筛选、分类样例、属性 include 和私有输出保护。Mihomo 检查使用合成的本地订阅，无真实账号或公网代理。选择测试只在临时进程上打开带测试口令的 `127.0.0.1` 控制接口，测试后关闭，**不会写入交付配置**。

CI 下载固定版本和校验值的官方 Mihomo，仅做上述离线/回环测试。未覆盖 FlClash UI、Stash 真机、真实订阅协议、实际 DNS/网络出口；通过 CI 不代表这些已验收。首次使用请分别测试微信、B站、AI、GitHub、YouTube 等，并在客户端连接日志核对命中组。

## 设计参考

- [用户原 QX 模板](https://ddgksf2013.top/Profile/QuantumultX.conf)：参考用途组/地区组结构，不复制脚本或安全弱化设置。
- [Repcz Mihomo](https://github.com/Repcz/Tool/blob/X/mihomo/Client/config.yaml) 与 [Stash](https://github.com/Repcz/Tool/blob/X/Stash/Stash.yaml)：参考组织方式；配置为独立实现。
- [Mihomo 代理集合](https://wiki.metacubex.one/config/proxy-providers/)；[Stash 代理集合](https://stash.wiki/proxy-protocols/proxy-providers)；[Stash 策略组](https://stash.wiki/proxy-protocols/proxy-groups)。
