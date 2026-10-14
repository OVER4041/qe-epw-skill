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

EPW 5.8.1 在 epw_readin.f90 中将通常设定的 dis_win_min（大于 -9999）重置为 -9999，因此输入中的常规下边界不会生效。检查器提示这一行为，不再按这个被忽略的参数判定窗口次序或冻结下边界。按实际带序用 bands_skipped 控制需要排除的低能带，不能仅凭元素名称猜半芯带数。dis_win_max、dis_froz_min 和 dis_froz_max 仍需检查；冻结窗口中的状态数不能超过 nbndsub，绝对能量参考也要与该次 QE 输出一致。

常规 Gamma 中心粗网格应使各方向的 nk 是 nq 的整数倍，让 k+q 仍在完整 NSCF 网格上。不能只检查两个网格的总点数。细网格是否有额外相容性要求则取决于目标算法，例如 ephwrite 与一般谱插值的条件不同。

首次流程通常使用 wannierize=.true.、epwread=.false.、epwwrite=.true.。epbwrite/epbread 是粗 Bloch 电子声子数据的写入/读取；它们与 Wannier checkpoint 的 epwwrite/epwread 是不同层级。

Wannier 重启采用 epwread=.true.、wannierize=.false.；先确认已有 checkpoint 与这次版本和粗网格一致。EPW 5.8.1 的主程序仍会在不做 Wannier 时读取 prefix.ukk，不能只复制 epmatwp。

scripts/check_runtime.py 的 checkpoint 模式只检查已核对的基本同目录布局：epwdata.fmt、vmedata.fmt、crystal.fmt、prefix.epmatwp、prefix.ukk 均非空；以该目录作为工作目录并设置 outdir='./'。其他文件布局、极性、偶极矩和力常数等模式需要检查附加依赖。文件存在不验证代码版本、二进制格式、粗网格、带子空间或物理收敛，不跨版本假定兼容。

若要重做 Wannier，应使用匹配的粗 Bloch 数据路径，不能将 epwread 重启混作首次 Wannier 流程。复用 epbread 数据时核对 epb 文件的池拆分，并保持与写入时一致的池数；不要用新的池数读取旧拆分数据。

a2f=.true. 要配合 phonselfen=.true.，输出普通和输运谱。不要因含有 a2f 就把算例称为已计算热导率。普通谱 α²F、输运谱 α²Ftr、电子自能和迭代输运有不同用途。

代码只接受真实 namelist 参数；不要把源码注释里的历史参数或变量声明全部当成输入键。此版 inputepw 中没有 ecutwfc、tempsmin、tempsmax 或 kmaps。kmaps 在该源码中属于内部变量，不能照抄新版网页作为输入。PW 的 ecutwfc 在 QE 数据阶段设定。

输运版本边界：`transport.f90` 的旧例程 `scattering_rate_q` 对金属报错，但这不等于整版不支持金属 IBTE。QE 7.3.1 的 `ephwann_shuffle.f90` 仅在 `scattering=.true.`、`iterative_bte=.false.` 且 `etf_mem<3` 时调用该例程；`iterative_bte=.true.` 走 `print_ibte` / `transport_iter`，后者明确含金属分支。该版 IBTE 要求相同的均匀细 k/q 网格。按完整调用链判断限制，不能把一个例程的报错推广到其他算法。

官方 EPW 6.0 发布说明列出了 `assume_metal` 的 IBTE 布居修复。使用 5.8.1 得到正式金属输运结果前，应核对具体构建是否含该修复，或在修复版本上验证；不要仅凭输入通过就认为结果可靠。旧例程的限制不妨碍输运谱/Ziman 路线，但后者与迭代 BTE 的计算近似不同。

电子热导复现还要核对输出和算法：5.8.1 的标准 IBTE 打印电导张量；`IBTEvel_sup.fmt` 保存速度、能量和权重，但 `transport_iter.f90` 默认将最终 `F_in` 写出调用注释掉了，`mobility_nk.fmt` 的条件也主要针对半导体载流子。不能假定标准日志已含独立电子热导、Seebeck 系数或完整金属状态分辨张量。论文使用自定义 BTE 求解器时，需要确认热流驱动项、能量权重、开路修正与单位，或实现并验证相应导出/求解。

官方来源：
- https://docs.epw-code.org/tutorials/tutorial_01/index.html
- https://raw.githubusercontent.com/QEF/q-e/qe-7.3.1/EPW/src/epw_readin.f90
- https://raw.githubusercontent.com/QEF/q-e/qe-7.3.1/EPW/src/epwcom.f90
- https://raw.githubusercontent.com/QEF/q-e/qe-7.3.1/EPW/src/epw.f90
- https://raw.githubusercontent.com/QEF/q-e/qe-7.3.1/EPW/src/loadbm.f90
- https://raw.githubusercontent.com/QEF/q-e/qe-7.3.1/EPW/src/transport.f90
- https://raw.githubusercontent.com/QEF/q-e/qe-7.3.1/EPW/src/ephwann_shuffle.f90
- https://raw.githubusercontent.com/QEF/q-e/qe-7.3.1/EPW/src/transport_iter.f90
- https://raw.githubusercontent.com/QEF/q-e/qe-7.3.1/EPW/src/printing.f90
- https://docs.epw-code.org/Releases.html
- https://docs.epw-code.org/Inputs/Inputs.html
