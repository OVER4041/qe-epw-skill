---
name: qe-epw
description: 为 Quantum ESPRESSO 和 EPW 编写、修改和检查输入文件及阶段衔接；用于 pw.x、ph.x、epw.x、DFPT、Wannier 插值、电子声子耦合与输运输入准备。
---

# QE / EPW 输入助手

把用户给出的结构、赝势、目标与已有数据转换为版本匹配、可检查的输入文件。常规格式使用本地参考和工具，已覆盖流程不必每次联网查手册。

## 先确定边界

- 区分只写输入、检查旧算例、后处理、运行新作业。写输入本身不授权新增收费计算；用户已要求运行时沿用已有授权，不重复索要许可。
- 从可用日志确认实际 QE 与 EPW 版本，不能仅靠安装目录名称判断。当前缓存完整核对了 QE 7.3.1 / EPW 5.8.1；官网在线输入页已是 EPW 6.1。
- 保留用户已有参数和有效数据。不要把 Cu 示例的截断能、半芯带、网格或冻结窗口当成通用已收敛默认值。
- 缺少结构、赝势、目标温度或版本时，先检查已有输入及日志；仅询问影响结果的缺项。

## 按需读取

- 写 SCF / NSCF / PH 输入：读 [references/qe-inputs.md](references/qe-inputs.md)。
- 写 Wannier / EPW 首次计算或重启：读 [references/epw-inputs.md](references/epw-inputs.md)。
- 组织数据、准备 Slurm 或分析输运：读 [references/workflow.md](references/workflow.md)。
- 换版本、使用缓存未覆盖功能：读 [references/versions.md](references/versions.md)，再查对应发布版的官方文档或输入源码。不要用最新页的拼写盲目替换旧版键名。

## 常规生成与检查

以技能目录为基准运行脚本：

    python scripts/render_inputs.py --case /absolute/path/case.json --output /absolute/path/new-inputs

case.json 的字段见 assets/case.example.json。工具生成 SCF、PH、完整 Gamma 中心粗 k 网格 NSCF、EPW 首次计算和 EPW 重启输入；可用 --stages 只生成需要的阶段。示例只是格式起点，需要按赝势和实际能带调整。

    python scripts/check_inputs.py /absolute/path/new-inputs/*.in

Windows 下若 shell 不展开通配符，直接传目录：

    python scripts/check_inputs.py /absolute/path/new-inputs

检查器检查版本固定的参数名、基本 Fortran 格式、重要标志组合和跨文件 prefix/outdir/grid。它不会证明收敛、能带插值正确、赝势合适或所有运行时组合可用。

## 必须保留的工程约束

- QE 截断能与 degauss 是 Ry；EPW degaussw/fsthick/能窗是 eV，degaussq 是 meV，temps 是 K。输入中写明单位，不能因为名字相近而沿用数值。
- EPW 5.8.1 的 &inputepw 没有 ecutwfc、tempsmin 或 tempsmax。ecutwfc 属于 pw.x；temps 用温度数组，范围模式要按该版本规则设置。
- PH 要保存非空 fildvscf，并为 EPW 整理与该次 DFPT 一致的 dyn/dvscf 数据。粗 k/q 网格要匹配 NSCF/PH，而不是细插值网格。
- EPW 5.8.1 源码要求 npool × nimage = nproc。通常单 image 时使用 -nk 等于 MPI 进程数；其他版本先核实对应并行实现。
- 重启输入不重做 Wannier；先核对 checkpoint 版本、prefix、粗网格和所需文件。不要仅凭文件存在就跨版本复用。
- 本地检查和输出预览通过后，再根据用户授权提交。使用 scnet-hpc MCP 时先检测连接，选择已配置 qe/epw 环境，保留 #SBATCH 资源设置并使用稳定 request_id 去重。按工具实际参数操作，不给旧接口传不存在的 environment 参数。
- 读结果时把数值完成、格式检查通过和物理收敛分开。费米能偏移、负谱/线宽、插值误差或未检查的网格应明确记录。
- 电子热导的 WF 估计与独立热流求解、晶格热导不是同一结果；保留用户选择的近似并清楚标注。

交付时提供输入文件、实际使用的版本、关键参数及单位、阶段依赖、检查结果和仍需验证的物理假设。
