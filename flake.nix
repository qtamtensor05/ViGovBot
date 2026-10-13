{
  description = "ViGovBot development environment (Python + uv)";

  inputs = {
    nixpkgs.url = "github:NixOS/nixpkgs/nixos-unstable";
  };

  outputs = {
    self,
    nixpkgs,
  }: let
    systems = [
      "x86_64-linux"
      "aarch64-linux"
      "x86_64-darwin"
      "aarch64-darwin"
    ];
    forAllSystems = nixpkgs.lib.genAttrs systems;
  in {
    devShells = forAllSystems (
      system: let
        pkgs = import nixpkgs {inherit system;};

        python = pkgs.python312;
        linuxLibs = with pkgs; [
          stdenv.cc.cc.lib
          zlib
          openssl
          libffi
        ];
        linuxLibPath = pkgs.lib.makeLibraryPath linuxLibs;

        maybeOllama = pkgs.lib.optionals (pkgs ? ollama) [pkgs.ollama];
      in {
        default = pkgs.mkShell {
          packages =
            [
              python
              pkgs.uv
              pkgs.git
              pkgs.tesseract
              pkgs.cacert
            ]
            ++ pkgs.lib.optionals pkgs.stdenv.isLinux linuxLibs;

          shellHook =
            ''
              export UV_PYTHON=${python}/bin/python

              export SSL_CERT_FILE=${pkgs.cacert}/etc/ssl/certs/ca-bundle.crt
              export REQUESTS_CA_BUNDLE=$SSL_CERT_FILE

              export TESSDATA_PREFIX=${pkgs.tesseract}/share/tessdata
            ''
            + pkgs.lib.optionalString pkgs.stdenv.isLinux ''
              export LD_LIBRARY_PATH=${linuxLibPath}:''${LD_LIBRARY_PATH:-}
            ''
            + ''
              echo "ViGovBot nix devShell loaded."
              echo "Next: uv venv --seed"
              echo "      uv pip install -e '.[test,dev]'"
            '';
        };

        rag = pkgs.mkShell {
          packages =
            [
              python
              pkgs.uv
              pkgs.git
              pkgs.tesseract
              pkgs.cacert
            ]
            ++ maybeOllama
            ++ pkgs.lib.optionals pkgs.stdenv.isLinux linuxLibs;

          shellHook =
            ''
              export UV_PYTHON=${python}/bin/python

              export SSL_CERT_FILE=${pkgs.cacert}/etc/ssl/certs/ca-bundle.crt
              export REQUESTS_CA_BUNDLE=$SSL_CERT_FILE

              export TESSDATA_PREFIX=${pkgs.tesseract}/share/tessdata
            ''
            + pkgs.lib.optionalString pkgs.stdenv.isLinux ''
              export LD_LIBRARY_PATH=${linuxLibPath}:''${LD_LIBRARY_PATH:-}
            ''
            + ''
              echo "ViGovBot RAG nix devShell loaded."
              echo "Next: uv venv --seed"
              echo "      uv pip install -e '.[rag]'"
              echo "      ollama pull qwen2.5:7b"
            '';
        };
      }
    );
  };
}
