# qe-epw skill

为 Quantum ESPRESSO / EPW 准备输入文件的 Codex skill。把已核对的格式、单位、版本差异和阶段依赖保存在本地，减少重复翻手册。

## 已覆盖的版本与流程

- QE **7.3.1** / EPW **5.8.1**：常规输入生成及静态检查。
- SCF → PH / DFPT → dyn/dvscf 整理 → 完整粗 k 网格 NSCF → EPW 首次计算 → Wannier 数据重启。
- 参数单位注释、版本固定的关键字检查、完整 k 网格、粗 k/q 相容性、能窗及重启标志检查。
- 金属输运的版本限制、结果单位转换和 Wiedemann–Franz 电子热导近似说明。

[EPW 在线输入页](https://docs.epw-code.org/Inputs/Inputs.html)目前对应 6.1，不能将其中所有参数直接用于 5.8.1。离线关键字注册表来自 [QEF 官方 qe-7.3.1 发布版源码](https://github.com/QEF/q-e/tree/qe-7.3.1)，保存来源 URL 与 SHA256。其他版本或高级功能需要先核对相应官方资料。

## 安装到 Codex

在 Codex 中输入：

```text
$skill-installer 从 https://github.com/OVER4041/qe-epw-skill 安装 skills/qe-epw 目录中的 skill。
```

也可以将完整的 `skills/qe-epw` 文件夹放到当前项目的 `.agents/skills/qe-epw`，或个人的 `~/.agents/skills/qe-epw`。同名 skill 只保留一个安装位置，避免重复加载。Codex 会自动检测技能；若未显示，重启 Codex。参见 [OpenAI 官方技能说明](https://learn.chatgpt.com/docs/build-skills)。

随后使用：

```text
$qe-epw 根据已有结构和赝势，为 300 K 输运准备 QE/EPW 输入，检查网格、能窗和重启条件。只写输入。
```

## 单独使用输入工具

运行时仅需 Python **3.10+**，不依赖第三方 Python 包，也不需要在超算上安装 Codex。

在仓库根目录执行：

```sh
python skills/qe-epw/scripts/render_inputs.py --case skills/qe-epw/assets/case.example.json --output generated-inputs
python skills/qe-epw/scripts/check_inputs.py generated-inputs
```

目录方式适用于 Windows、Linux 和 macOS。生成器不会覆盖已有输入集。先复制 `assets/case.example.json` 并填写实际结构、赝势、网格、能带数和 Wannier 设置；用 `--stages scf,ph,nscf` 等选项只生成需要的阶段。

输出包含五阶段输入及 `input-manifest.json`。案例 JSON 中的版本必须与缓存匹配；QE 能量以 Ry 输入，EPW 能窗及电子展宽用 eV，声子展宽用 meV，温度用 K。主要单位会写入输入注释。

Cu 示例是非磁性 FCC、19 电子 NC 赝势的格式样例；没有附带真实赝势、DFPT 数据或 checkpoint。其截断能、能窗、投影及网格不能视为已收敛参数。实际计算还需选择自己的运行环境、工作目录和调度资源。

## 验证范围

```sh
python -B -m unittest discover -s tests -v
```

23 项离线回归检查覆盖生成流程、版本边界、非法参数、非立方完整网格、粗 k/q 相容性、能窗、重启、数值及文件覆盖保护。GitHub Actions 在 Windows/Linux、Python 3.11/3.14 上运行同一组检查。

静态检查通过表示通过了本工具覆盖的条件，不代表完整 Fortran 解析、所有算法组合可运行或物理收敛。赝势、Wannier 能带/速度插值、冻结态数量和目标物性的收敛仍需验证。输入准备不会自动接入超算或提交作业；已有 [scnet-hpc MCP](https://github.com/OVER4041/mcp-scnet-hpc) 可作为单独的运行接口。

## 目录

```text
skills/qe-epw/
  SKILL.md             使用规则与参考路由
  agents/openai.yaml   Codex 显示信息
  assets/              案例配置与版本关键字注册表
  references/          QE、EPW、阶段依赖和版本说明
  scripts/             输入生成与静态检查
tests/                离线回归检查
```

原创代码与说明采用 MIT 许可。上游资料来源和范围见 [NOTICE.md](NOTICE.md)。
