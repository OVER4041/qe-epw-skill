# EPW 5.8.1 常用输入参考

本参考对应 QE 7.3.1 自带 EPW 5.8.1。网页最新文档可能对应其他版本；离线参数名从实际 &inputepw 源码提取。

输入可在 &inputepw 前放一行普通标题。这一版读入程序也能识别第一行直接为 &inputepw 并回退为默认标题，因此生成器使用无标题的格式。该行为是版本实现细节，不应自动推广到所有程序和版本。

| 参数 | 单位/作用 |
|---|---|
| prefix、outdir | 对应 QE NSCF 数据，不是任意输出标签 |
| dvscf_dir | 整理后的响应势和动力学矩阵目录 |
| amass(i) | 各物种质量；与 QE 物种顺序一致 |
| nk1..nk3 | NSCF 的粗 k 网格 |
| nq1..nq3 | DFPT 的粗 q 网格 |
| nkf1..nkf3、nqf1..nqf3 | 细插值网格，需单独做收敛 |
| nbndsub | Wannier 子空间维数，不等于总原始 nbnd |
| bands_skipped | 传给 Wannier 的排除带说明；根据赝势及原始能带判断 |
| proj(i) | Wannier 投影；不要把材料名称直接套到另一种材料 |
| dis_win_*、dis_froz_* | eV，使用 QE 能带的绝对能量参考，不自动把 Ef 当作零点 |
| degaussw、fsthick | eV |
| degaussq、delta_qsmear | meV |
| temps | K 数组，例如 temps(1)=300；多温度可逐项赋值 |
| nstemp | 温度数量；两个端点配合更大 nstemp 可生成等间距列表 |
| ngaussw | 0 为 Gaussian，正整数为 MP；数值影响负权重和收敛行为 |
| eps_acustic | 该版拼写，无第二个 o；声学低频阈值，cm⁻¹ |

常规 Gamma 中心粗网格应使各方向的 nk 是 nq 的整数倍，让 k+q 仍在完整 NSCF 网格上。不能只检查两个网格的总点数。细网格是否有额外相容性要求则取决于目标算法，例如 ephwrite 与一般谱插值的条件不同。

首次流程通常使用 wannierize=.true.、epwread=.false.、epwwrite=.true.。epbwrite/epbread 是粗 Bloch 电子声子数据的写入/读取；它们与 Wannier checkpoint 的 epwwrite/epwread 是不同层级。

Wannier 重启采用 epwread=.true.、wannierize=.false.；先确认已有 checkpoint 与这次版本和粗网格一致。检查 epwdata.fmt、对应 epmatwp、结构/速度数据等实际依赖，不跨版本假定文件兼容。

a2f=.true. 要配合 phonselfen=.true.，输出普通和输运谱。不要因含有 a2f 就把算例称为已计算热导率。普通谱 α²F、输运谱 α²Ftr、电子自能和迭代输运有不同用途。

代码只接受真实 namelist 参数；不要把源码注释里的历史参数或变量声明全部当成输入键。此版 inputepw 中没有 ecutwfc、tempsmin、tempsmax 或 kmaps。kmaps 在该源码中属于内部变量，不能照抄新版网页作为输入。PW 的 ecutwfc 在 QE 数据阶段设定。

输运版本边界：此版 transport.f90 的 scattering_rate_q 对 assume_metal 显式报 metals not implemented。金属电阻率可以用输运谱/Ziman 路线，但不能自动套用半导体的 mobility / IBTE 开关组合。版本更新后再核对限制是否解除。

官方来源：
- https://docs.epw-code.org/tutorials/tutorial_01/index.html
- https://raw.githubusercontent.com/QEF/q-e/qe-7.3.1/EPW/src/epw_readin.f90
- https://raw.githubusercontent.com/QEF/q-e/qe-7.3.1/EPW/src/epwcom.f90
- https://raw.githubusercontent.com/QEF/q-e/qe-7.3.1/EPW/src/transport.f90
- https://docs.epw-code.org/Inputs/Inputs.html
