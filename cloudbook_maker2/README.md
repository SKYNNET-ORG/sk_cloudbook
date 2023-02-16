# cloudbook_maker2

Requirements: PLY , radon, astunparse

Check you are using pip3 tool ( if you have python2 and python3 probably you have both pip tools)
  - (install ply: pip install ply)
  - (install radon: pip install radon)
  - (install asteunparse: pip install astunparse)
  
Usage:
python3 cloudbook_maker.py -project_folder <project_folder> [-matrix <filematrix.json>] [-log <debug|info|warning|error|critical|all>]

    where:
      -matrix filematrix.json is an optional parameter used for
                              remaking a program using new matrix values
      -log level is an optional parameter used for show traces of the execution
                              by default the log is made in a file.
