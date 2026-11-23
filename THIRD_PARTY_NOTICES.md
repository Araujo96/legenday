# Componentes de terceiros

O legenDay (licença MIT, veja `LICENSE`) usa os componentes abaixo. O pacote para Windows os traz junto,
cada um em arquivos separados dentro da pasta do programa (`_internal`), o que permite substituí-los por outras versões.

| Componente | Uso | Licença | Código-fonte |
|---|---|---|---|
| mpv / libmpv (`libmpv-2.dll`) | reprodução do vídeo | GPL-2.0+ (LGPL-2.1+ nas builds feitas para isso)* | https://github.com/mpv-player/mpv |
| Build do libmpv para Windows | compilação do mpv | conforme o mpv | https://github.com/shinchiro/mpv-winbuild-cmake |
| FFmpeg (`ffmpeg.exe`, build LGPL) | ler legendas embutidas | LGPL-2.1+ | https://github.com/FFmpeg/FFmpeg · builds: https://github.com/BtbN/FFmpeg-Builds |
| Qt 6 / PySide6 | interface | LGPL-3.0 (ou GPL) | https://code.qt.io · https://pypi.org/project/PySide6/ |
| python-mpv | ligação do Python com o mpv | GPL-2.0+ ou LGPL-2.1+ | https://github.com/jaseg/python-mpv |
| pysubs2 | leitura de legendas | MIT | https://github.com/tkarabela/pysubs2 |
| simplemma | forma base das palavras | MIT | https://github.com/adbar/simplemma |
| Python | linguagem | PSF License | https://www.python.org |
| PyInstaller | geração do executável | GPL-2.0+ com exceção que não afeta os programas gerados | https://github.com/pyinstaller/pyinstaller |

\* O arquivo `libmpv-2.dll` incluído vem de uma build de terceiros. Confira a licença da build usada ao redistribuí-la.

Serviços online usados durante o uso do app (nada disso vai dentro do pacote): MyMemory (tradução),
Free Dictionary API (definições) e Wikimedia Commons (gravações de pronúncia, tocadas direto de lá, sob a licença
livre de cada arquivo). Veja a aba **Sobre** da ajuda para a nota de privacidade.

As imagens e o vídeo de demonstração em `docs/` mostram cenas de *Tears of Steel* (CC BY 3.0) © Blender Foundation,
mango.blender.org.

Este arquivo é informativo e não substitui as licenças originais de cada projeto.
