{ pkgs }: {
  deps = [
    pkgs.python312
    pkgs.python312Packages.pip
    pkgs.go
    pkgs.nodejs_20
    pkgs.git
    pkgs.curl
    pkgs.coreutils
  ];
}
