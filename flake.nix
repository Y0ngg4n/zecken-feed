{
  pkgs,
  lib,
  config,
  inputs,
  ...
}:

{
  languages.python = {
    enable = true;
    venv.enable = true;
    venv.requirements = ''
      black
      fastapi
      fastapi-cli
      pytest
      feedgen
      signalbot
      requests
      setuptools
      build
      wheel

    '';
  };

  enterShell = ''
    python -c "import PySide2" && echo "No errors!"
  '';
}
