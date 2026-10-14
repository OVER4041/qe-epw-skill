# Sources and scope

The skill is an independent input-preparation helper. Quantum ESPRESSO and EPW are upstream scientific software maintained by their respective developers; this project is not an official distribution or endorsement.

The release-specific keyword registry was extracted from the QEF official `qe-7.3.1` source files. It stores keyword identifiers, source URLs and SHA256 values. It does not bundle the upstream implementation, executables, pseudopotentials or complete manuals. The MIT license in this repository applies to its original helper code and explanatory material, not to upstream software or documentation.

Primary references:

- EPW input documentation: https://docs.epw-code.org/Inputs/Inputs.html
- EPW tutorials: https://docs.epw-code.org/Tutorials.html
- EPW coarse-grid tutorial: https://docs.epw-code.org/tutorials/tutorial_01/index.html
- QE PW input documentation: https://www.quantum-espresso.org/Doc/INPUT_PW.html
- QE PH input documentation: https://www.quantum-espresso.org/Doc/INPUT_PH.html
- QEF release source: https://github.com/QEF/q-e/tree/qe-7.3.1
- EPW release notes and metal IBTE fix: https://docs.epw-code.org/Releases.html
- EPW 5.8.1 input and completion implementation: https://github.com/QEF/q-e/blob/qe-7.3.1/EPW/src/epw_readin.f90 and https://github.com/QEF/q-e/blob/qe-7.3.1/EPW/src/stop_epw.f90
- Wannier90 convergence implementation: https://github.com/wannier-developers/wannier90/blob/v3.1.0/src/wannierise.F90

The keyword snapshot was checked on 2026-10-12; restart, completion and transport references were reviewed through 2026-10-14. The online EPW input index is for v6.1; the included generator and keyword checks are fixed to QE 7.3.1 / EPW 5.8.1. Source hashes in the registry identify the snapshot and are not verification of a user's executable build. Runtime checks cover only the documented basic restart layout and completion markers, not every EPW mode or physical convergence.
