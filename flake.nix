{
  description = "ViGovBot development environment";

  inputs.nixpkgs.url = "github:NixOS/nixpkgs/nixos-unstable";

  outputs = { self, nixpkgs }:
    let
      system = "x86_64-linux";
      pkgs = import nixpkgs { inherit system; };

      python = pkgs.python312.withPackages (ps: with ps; [
        pip
        setuptools
        wheel
      ]);
    in
    {
      devShells.${system}.default = pkgs.mkShell {
        packages = with pkgs; [
          python
          uv
          stdenv.cc
          git
          pkg-config
          openssl
          zlib
          libffi
        ];

        LD_LIBRARY_PATH = pkgs.lib.makeLibraryPath [
          pkgs.stdenv.cc.cc.lib
          pkgs.zlib
          pkgs.openssl
          pkgs.libffi
        ];

        shellHook = ''
          export LD_LIBRARY_PATH="/run/opengl-driver/lib''${LD_LIBRARY_PATH:+:$LD_LIBRARY_PATH}"
          export LD_PRELOAD="/run/opengl-driver/lib/libcuda.so.1''${LD_PRELOAD:+:$LD_PRELOAD}"
          export PYTHONPATH="$PWD/src''${PYTHONPATH:+:$PYTHONPATH}"
          echo "ViGovBot development environment"
          python --version
        '';
      };
    };
}
