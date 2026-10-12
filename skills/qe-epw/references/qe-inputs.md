# QE 常用输入参考

核对日期：2026-10-12。离线键名快照来自 QEF 官方 qe-7.3.1 发布版。语法和本地工具仅覆盖常规 pw.x/ph.x 流程；CP、NEB、RISM 等另行核对相应程序。

## pw.x

一般顺序为 &CONTROL、&SYSTEM、&ELECTRONS，各段用 / 结束，然后 ATOMIC_SPECIES、ATOMIC_POSITIONS、K_POINTS；ibrav=0 还需 CELL_PARAMETERS。

| 内容 | 注意事项 |
|---|---|
| calculation | scf / nscf 等字符串，不是布尔值 |
| prefix/outdir | 后续 PH、NSCF、EPW 要指向相同的有效数据 |
| pseudo_dir | 目录相对运行工作目录，不相对输入文件目录 |
| ibrav、A / celldm | 按一种晶胞约定填写，避免混用长度单位 |
| nat、ntyp | 与位置行数、物种行数一致 |
| ecutwfc、ecutrho | Ry；根据赝势和收敛测试设定，不能默认所有赝势都用 4 倍密度截断 |
| occupations、smearing、degauss | degauss 为 Ry；金属需要合适的占据处理 |
| conv_thr | 自洽阈值；数值严格不等于网格已收敛 |
| nbnd | NSCF 的原始 Bloch 带数，需容纳 Wannier 子空间及排除带 |

字符串加引号，逻辑值写 .true./.false.，双精度指数可以用 d。数组可写为 name(1)=value。生成的科学输入优先使用 ASCII 文本和 LF 换行；注释用 !，引号内的 ! 属于字符串。

SCF 可以使用对称性约化的自动网格。供 EPW 使用的 NSCF 通常需要完整均匀粗 k 网格；生成工具使用 K_POINTS crystal 显式列出 Gamma 中心网格，并设置 nosym/noinv。不要用高对称路径替代粗网格。生成器把权重归一到 1；QE 的 NSCF 特征值/波函数不依赖点权重，等权全写为 1 也合法。

## ph.x

常规网格输入用 &inputph，包括 prefix、outdir、tr2_ph、ldisp、nq1/nq2/nq3、fildyn、fildvscf。QE 7.3.1 的 phq_readin 允许第一行直接是 &inputph，并使用默认标题；也可先放一行普通标题。fildvscf 不能留空，否则后续电子声子阶段缺少响应势。

对金属不要自动启用介电常数/极化设置。单 q 点模式与 ldisp 网格模式的附加坐标格式不同；生成工具只提供 ldisp 网格模式。

PH 应读取 SCF 状态。若共用 scratch，先完成 PH，再让 NSCF 改写对应保存数据；并行分支可使用独立 scratch 的 SCF 副本。原始文件目录、池拆分和代码版本会影响 dvscf 组织，按匹配版本的官方整理工具处理。

官方来源：
- https://raw.githubusercontent.com/QEF/q-e/qe-7.3.1/PW/Doc/INPUT_PW.def
- https://www.quantum-espresso.org/Doc/INPUT_PW.html
- https://www.quantum-espresso.org/Doc/INPUT_PH.html
- https://raw.githubusercontent.com/QEF/q-e/qe-7.3.1/Modules/input_parameters.f90
- https://raw.githubusercontent.com/QEF/q-e/qe-7.3.1/PHonon/PH/phq_readin.f90
