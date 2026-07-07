# TA for DeepL Translator
This add-on provides custom search command "translate" which translates field values using DeepL Translator.

## Getting Started
Before you start, you need to have API key. If you don't have one, you cant obtain one at https://www.deepl.com/pro-api.
If you have one, input it in "Set up" from Apps list page.

## Usage
Example:
```| translate <source_field>```
By default, text in source_field are tranlslated into Japanese, which are stored in “translated” field. 
You can change the target language from Japanese to another using "t_lang" option.
Source language is determined automatically by DeepL.

Example:
```| translate t_lang="EN" <source_field>```
The languages that can be specified for "t_lang" depend on DeepL, see link below.
 https://www.deepl.com/docs-api/translate-text/
# Binary File Declaration
