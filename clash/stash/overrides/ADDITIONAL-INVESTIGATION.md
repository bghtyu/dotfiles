# 追加四项配置调查记录（2026-11-05）

本次没有为这四项新增可导入的 `.stoverride`。找到的现成版本未同时满足“可靠、功能范围可确认、全部运行时依赖可固定、完整复制许可可建立”的条件；没有把 Quantumult X 文件直接当 Stash 配置，也没有把精选子集称为等价。原有三个覆写仍可单独启停，MITM 范围未因此扩大。

原配置、候选及抽查脚本的下载 URL、固定提交、大小和 SHA-256 见 [additional-investigation.json](additional-investigation.json)。未复制未获许可的配置或脚本正文到仓库。此处的指纹不是客户端会加载的依赖。

| 项目 | 已核实情况 | 本 PR 处理 |
| --- | --- | --- |
| [General](https://github.com/ddgksf2013/Rewrite/blob/dc3ea2c1fb2db870676b26da24006083eb1d44d3/Html/General.conf) | 原文件只有 Google 中国域名到 www.google.com 的 302 和 www.google.cn MITM，无 JS；它不是通用去广告规则。未建立有明确复制许可、可直接纳入的现成 Stash 版本。原匹配式较宽，不能未经评估原样推广。 | 记录结果，未复制/转换。若另行实现，应独立限定域名、保留路径/参数并单独测试；这不是已找到并获许可的现成版本。 |
| [CaiYunAds](https://github.com/ddgksf2013/Rewrite/blob/dc3ea2c1fb2db870676b26da24006083eb1d44d3/AdBlock/CaiYunAds.conf) | 原 QX 配置引用一个浮动 caiyun_json.js，含广告净化和两条旧版用户会员状态伪装规则；前者已列四个 MITM 主机，后者要求用户另加 biz.cyapi.cn。抽查固定 JS 确认会修改 is_vip、svip 到期等字段。没有确认可合法再分发的、纯广告且功能等价/完整 MITM 的原生 Stash 版本。 | 不把会员伪装静默加入“去广告”，不新增脚本或 MITM。ddgksf2013/Scripts 固定版本无 LICENSE，授权链仍不明确。 |
| [StartUpAds](https://ddgksf2013.top/rewrite/StartUpAds.conf) | 使用 Quantumult X User-Agent 获得实际 QX 配置，记录下载字节指纹。包含数百条重写、437 个独立 MITM 条目（含通配符/IP）及 25 个唯一远程 JS 地址，覆盖金融、医疗等敏感 App 域名，多个脚本/配置还使用浮动分支。现成精选/转换版不能证明与整包等价；不能继承整包的授权和安全结论。 | 没有整包扩大解密范围。保留 25 个 URL 的研究清单；未完成这 25 个脚本的全部依赖/安全审计，不能称已审计或固定。多个源脚本许可不明，在完整许可与范围决策前不准入。 |
| [AmapAds](https://github.com/ddgksf2013/Rewrite/blob/dc3ea2c1fb2db870676b26da24006083eb1d44d3/AdBlock/AmapAds.conf) | 原版含 m5/m5-zb/center/amap-aos-info-nogw/ai 主机、optimus-ads DIRECT 路由及浮动 amap.js、amdc.js，后者处理明文 HTTP amdc.m.taobao.com；amap.js 有混淆代码，不能只据脚本名断言安全。已找到 [qsoyq 原生 Stash 高德覆写](https://github.com/qsoyq/stash/blob/81944fcb20ed576daca7b6363ff23a39c6f9dfe8/override/ad/amap.stoverride)，使用 response-jq，无远程 JS，但只覆盖部分开屏、首页/搜索，另带 force-http-engine，和墨鱼版的行为/范围不等价。 | qsoyq/stash 该提交未发现 LICENSE 或明确复制授权；原版 ddgksf2013 依赖许可同样未明确，不复制现成配置或混淆脚本，也不反向改变广告域名路由策略。 |

许可核对包括原 `ddgksf2013/Rewrite`、脚本 `ddgksf2013/Scripts` 和已下载原生候选 `qsoyq/stash` 的完整树/文件头。部分头部“引用请注明出处”没有清楚说明复制、改编和完整依赖的再分发范围；本次没有将其当作完整供应链授权。公开可读、其他人已搬运、或转换工具能输出 Stash 语法，都不自动解决原作品许可。其他规则仓库的总 LICENSE 也不能自动授予它所引用外部 JS 的权利。

本记录是候选准入调查，不是这四项完整脚本依赖闭包的安全审计。未进行真机/账号/流量测试，没有删除已用功能，没有按上游提示卸载 App，没有安装证书或改动设备设置。下一步应先获得相应权利人的许可，或明确选择可获许可、范围更小的替代功能，再逐项审查及固定；不能仅靠补上 hash 即宣布完成。
