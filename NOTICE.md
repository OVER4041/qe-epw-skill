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

References were checked on 2026-10-12. The online EPW input index is for v6.1; the included generator and keyword checks are fixed to QE 7.3.1 / EPW 5.8.1. Source hashes in the registry identify the snapshot and are not verification of a user's executable build.
