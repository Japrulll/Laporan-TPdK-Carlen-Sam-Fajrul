Template Laporan Tugas Akhir STI STEI
Institut Teknologi Bandung

Dokumen utama:
1. ProposalTA
2. daftar-pustaka.bib
3. ta-sti.cls

by baskara at itb dot ac dot id

Petunjuk penggunaan:
1.  Ada 3 file utama, yaitu 
    - ProposalTA.tex (file utama)
    - daftar-pustaka.bib (file daftar pustaka)
    - ta-sti.cls (class file)
    Ketiga file ini harus berada di folder yang sama.
2.  Sunting ProposalTA.tex sesuai dengan kebutuhan Anda.
3.  Sunting atau generate isi daftar-pustaka.bib dengan referensi yang Anda gunakan, sesuai dengan format BibLaTeX.
4.  Kompilasi file ProposalTA.tex menggunakan XeLaTeX dan Biber (lihat urutan cara kompilasi di bawah).
5.  Hasil kompilasi adalah file ProposalTA.pdf yang siap untuk dicetak.

Eksekusi perintah-perintah berikut untuk melakukan kompilasi melalui command line (cmd atau terminal):
    1. xelatex ProposalTA.tex
    2. biber ProposalTA      
    3. xelatex  ProposalTA.tex
    4. xelatex  ProposalTA.tex

Jika meenggunakan Visual Studio Code sebagai editor, pastikan menambahkan "latex-workshop.latex.tools" dan
    "latex-workshop.latex.recipes" di bawah ini di JSON User Settings:

"latex-workshop.latex.tools": [ 
       {
           "name": "xelatex",
           "command": "xelatex",
           "args": [
               "-synctex=1",
               "-interaction=nonstopmode",
               "-file-line-error",
               "%DOC%"
           ]
       },
       {
           "name": "biber",
           "command": "biber",
           "args": [
               "%DOCFILE%"
           ]
       }
   ],
   "latex-workshop.latex.recipes": [
       {
           "name": "xelatex -> biber -> xelatex*2",
           "tools": [
               "xelatex",
               "biber",
               "xelatex",
               "xelatex"
           ]
       }
   ]


Catatan:
 -  Pastikan Anda telah menginstal paket-paket LaTeX yang diperlukan, termasuk
    biblatex-chicago dan fontspec.
-   Gunakan editor LaTeX yang mendukung XeLaTeX, seperti TeXstudio, Overleaf, TexShop (Mac OS) atau lainnya.

