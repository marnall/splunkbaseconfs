日本語の半角の文字列を全角にするコマンド han2zen コマンドと全角の文字列を半角にする zen2han コマンドを提供します。
Python ライブラリmojimoji(https://github.com/studio-ousia/mojimoji) を Splunk から利用できるようにしたものです。

使い方:
| han2zen input_field outfield="zenkaku_field"
outfield は省略可能で、省略した場合、zen2han では "hankaku" フィールドに、han2zen では "zenkaku" フィールドに出力されます。

オプション:
カナ、数字、ASCII 文字列のうち特定の文字のみ変換対象から外したい場合、exclude オプションで変換対象から外すことができます。
| zen2han input_field outfield="hankaku_field" exclude="kana"
exclude=[kana|digit|ascii]
# Binary File Declaration
/opt/splunk/var/data/tabuilder/package/TA-mojimoji/lib/mojimoji.cpython-37m-x86_64-linux-gnu.so: this file does not require any source code
# Binary File Declaration
/opt/splunk/var/data/tabuilder/package/TA-mojimoji/lib/mojimoji.cpython-37m-x86_64-linux-gnu.so: this file does not require any source code
# Binary File Declaration
/opt/splunk/var/data/tabuilder/package/TA-mojimoji/lib/mojimoji.cpython-39-x86_64-linux-gnu.so: this file does not require any source code
