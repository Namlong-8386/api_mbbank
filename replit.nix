{pkgs}: {
  deps = [
    pkgs.libgbm
    pkgs.gtk3
    pkgs.gdk-pixbuf
    pkgs.atk
    pkgs.pango
    pkgs.cairo
    pkgs.expat
    pkgs.dbus
    pkgs.cups
    pkgs.alsa-lib
    pkgs.mesa
    pkgs.libdrm
    pkgs.libxkbcommon
    pkgs.xorg.libXtst
    pkgs.xorg.libXrender
    pkgs.xorg.libXrandr
    pkgs.xorg.libXfixes
    pkgs.xorg.libXext
    pkgs.xorg.libXdamage
    pkgs.xorg.libXcomposite
    pkgs.xorg.libX11
    pkgs.xorg.libxcb
    pkgs.nss
    pkgs.nspr
  ];
}
