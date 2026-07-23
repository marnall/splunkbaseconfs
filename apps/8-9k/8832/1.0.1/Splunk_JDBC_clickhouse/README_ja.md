# Splunk DBX Add-on for Clickhouse

## 概要
本アドオンは、Splunk DB Connect と ClickHouse（ClickHouse Cloud を含む）を連携させるためのカスタムJDBCドライバーアドオンです。Splunk公式からは ClickHouse 用のアドオンが標準提供されていないため、必要なJDBCドライバー本体とSplunk側の設定ファイルをパッケージ化し、Splunk Enterprise および Splunk Cloud へ簡単にインストールできるように作成されました。

## 変更点と仕様
- **同梱JDBCドライバー**: Maven Central から公式の `clickhouse-jdbc-all-0.9.8.jar` (v0.9.8) を直接ダウンロードして同梱しています。
- **統合ドライバーの採用**: Splunk DB Connect のクラスローダーによる依存関係の分断（複数のJARに分かれていると `NoClassDefFoundError` が発生する問題）を回避するため、ドライバーと全ての依存ライブラリが1つに統合された `all` アーティファクトを採用しています。
- **設定ファイルの追加**: Splunk DB Connect のUI上で「ClickHouse」をデータベースタイプとして自動認識させるため、`db_connection_types.conf` を独自に追加・設定済みです。

## インストール手順
1. Splunk の Web UI から「Appの管理」->「ファイルからAppをインストール」を選択し、本アドオンのパッケージ（.tgz）をアップロードします。
2. インストール後、**Splunk DB Connect** App を開きます。
3. **設定 (Configuration) > データベース (Databases) > ドライバー (Drivers)** タブへ移動し、右上の **再読込 (Reload)** ボタンを押します。
4. 一覧に「ClickHouse」が表示され、緑色のチェックマーク（インストール済）が付けば準備完了です。
