self: super: let
  overridePython = pypkgs: let
    packageOverrides = pyself: pysuper: {
        bugan = pysuper.callPackage ./../default.nix {};
    };
  in pypkgs.override { inherit packageOverrides; };
in {
  python3 = overridePython super.python3;
}
