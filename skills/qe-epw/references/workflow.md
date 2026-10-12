# 阶段衔接、超算与结果检查

## 选择阶段

SCF → PH/DFPT → 组织 dyn/dvscf → 完整粗 k 网格 NSCF → Wannier/粗电子声子数据 → 细网格插值/目标物性。可复用已经有效完成的阶段，不必重算全部流程。

- PH 使用 SCF 的数据与响应势。共用 scratch 时，NSCF 放在 PH 完成后，或为分支复制独立 SCF scratch。
- 以 prefix、结构、赝势、SCF/NSCF 截断与数据版本判断能否复用，不只看 JOB DONE。
- 同一出发数据上比较 Wannier 与 QE 能带、速度、费米能和声子频率。粗/细费米能不一致要查原因；不能单纯强行固定 Ef 掩盖插值问题。
- 检查冻结窗口中每个 k 点的状态数不超过 nbndsub，目标能区是否被正确表示。投影、窗口和半芯排除不能仅从元素名称猜测。
- 整理 phonon 数据使用版本匹配的官方 pp.py/epw_pp.py 工具或明确检查过的脚本；其文件布局会随版本、池和计算模式变化。

## Slurm / scnet-hpc

先查看可用接口和环境。若有 list_environments/check_environment/preview_job，按需要选择 qe 或 epw，并在 submit_job 中传 environment；旧接口不支持时，不传未知参数，改为在已审阅作业脚本中明确初始化环境。

不在登录节点运行大型 QE/EPW 计算。准备 #SBATCH 资源、工作目录、输入/日志路径和失败返回码。环境初始化放在全部开头 #SBATCH 指令之后，计算命令之前。若原脚本另有 module purge/source，检查是否会覆盖所选环境。

工作目录以提交时明确指定的目录为准；相对 outdir/pseudo_dir/dvscf_dir 都据此解析。注意脚本里的 cd $SLURM_SUBMIT_DIR 可能抵消 --chdir；不要照抄到不同的提交工作目录。

EPW 5.8.1 要满足 npool×nimage=nproc；单 image 示例可用 mpirun -np "$SLURM_NTASKS" epw.x -nk "$SLURM_NTASKS" -in epw.in。这不意味着其他版本或其他阶段的最优池数相同。

若用户授权运行，提交前核实脚本和资源，按稳定 request_id 去重。网络中断后先查队列/提交记录，不能盲目提交第二遍。Skill 本身不授予自动取消旧作业或覆盖计算目录的授权。

## 结果与输运

- 正常退出、JOB DONE、Wannier 迭代完成只是阶段完成；还要检查网格、电子展宽、响应势/插值和目标量的收敛。
- 模式分辨负 λ/linewidth 或谱负值可能涉及 MP 负权重和数值误差；不能直接宣布为材料不稳定，也不能忽略。
- EPW 金属 res 文件的 μΩ·cm 换为 Ω·m 乘 10⁻⁸，σ=1/ρ。按该次文件头确认单位及展宽列。
- WF 电子热导估计：κe=L0 σT，L0=(π²/3)(kB/e)²≈2.4430×10⁻⁸ W·Ω/K²。标为近似，不是独立热流 BTE 结果，不包含晶格热导。
- 晶格热导通常还需要非谐力常数及声子输运；QE+EPW 的现有电阻率文件不能直接给出总热导率。
- 单一细网格不能证明收敛；粗/细费米能差异应结合能带插值和数值积分诊断，不将个别算例数值当作新任务的默认答案。

相关官方资料：
- https://docs.epw-code.org/Tutorials.html
- https://arxiv.org/abs/1604.03525
- https://slurm.schedmd.com/sbatch.html
