## 概要
本 Add-on は、オープンソース 形態素解析エンジン MeCab を利用して日本語文章の形態素解析機能を提供します。具体的には MeCab の提供する下記の処理が実行可能です。

- 単語への分かち書き(tokenization)
- 活用語処理(stemming, lemmatization)
- 品詞同定(part-of-speech tagging)

## 使い始めるにあたって

本 Add-on には、辞書として unidic をバンドルしていますので、ひとまず辞書をダウンロードしてこなくても利用を開始することができます。

### 使い方(形態素解析)

```bash
| morph field="<src_field>" outfield="<out_field>"
```

`outfield`  はオプションで、指定しない場合 `morph` フィールドが使用されます。

### 使い方(分かち書き)

```bash
| wakati field="<src_field>" outfield="<out_field>"
```

`outfield`  はオプションで、指定しない場合 `wakati` フィールドが使用されます。
