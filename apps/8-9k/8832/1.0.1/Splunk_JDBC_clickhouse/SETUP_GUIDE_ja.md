# ClickHouse 接続設定ガイド (Splunk DB Connect)

本ドキュメントでは、本アドオン（Splunk DBX Add-on for Clickhouse）を使って、Splunk DB Connect から ClickHouse Cloud に接続するための具体的な手順を解説します。

## 1. 事前準備
1. Splunk 上で **Splunk DB Connect** App がインストールされ、Task Server が正常に起動していることを確認してください。
2. 本アドオン (`splunk-dbx-addon-for-clickhouse_100.tgz`) が Splunk にインストールされていることを確認してください。
3. ClickHouse Cloud 側の接続情報（エンドポイントの Host URL、Username、Password）を手元に用意します。
   - 例: Host: `xxxxxx.clickhouse.cloud`, Port: `443`, User: `default`

## 2. Identity (認証情報) の登録
DB Connect が ClickHouse にログインするためのユーザー名とパスワードを登録します。

1. Splunk 上のメニューから **Splunk DB Connect** を開きます。
2. **Configuration > Databases > Identities** タブに移動します。
3. 右上の **[New Identity]** ボタンをクリックします。
4. 以下の項目を入力し、**[Save]** をクリックします。
   - **Identity Name**: 任意の名前（例：`clickhouse_cloud_id`）
   - **Username**: ClickHouse のユーザー名（例：`default`）
   - **Password**: ClickHouse のパスワード

## 3. Connection (接続情報) の登録
実際に ClickHouse Cloud へ接続するための設定を作成します。

1. **Configuration > Databases > Connections** タブに移動します。
2. 右上の **[New Connection]** ボタンをクリックします。
3. 以下の項目を入力します。
   - **Connection Name**: 任意の接続名（例：`clickhouse_cloud`）
   - **Identity**: 先ほど「2」で作成した Identity（例：`clickhouse_cloud_id`）を選択
   - **Connection Type**: **`ClickHouse`** を選択
   - **Timezone**: データベース側のタイムゾーン（基本は `UTC` を推奨）
   - **Host**: ClickHouse Cloud のエンドポイント（例：`xxxxxx.gcp.clickhouse.cloud`）
   - **Port**: **`443`**（ClickHouse Cloud の SSL 接続用ポート）
   - **Default Database**: `default`（または利用したいデータベース名）

   > **ポートに関する注意**: ClickHouse Cloud はポート `443` と `8443` の両方で HTTPS 接続を受け付けます。本アドオンではデフォルトを `443` に設定しています。これは、**Splunk Cloud が非標準ポート（`8443` を含む）への送信トラフィックをデフォルトでブロックする**ためです。ポート `443` は Splunk Enterprise と Splunk Cloud の両環境で使用可能です。オンプレミスの Splunk Enterprise をご利用の場合は、ポート `8443` も使用できます。
4. **【重要】Enable SSL** のチェックボックスに必ず**チェックを入れます**。
   - これにより、内部的に `?ssl=true` オプションが付与され、ClickHouse Cloud とのセキュア通信が可能になります。
5. 下部の **[Save]** をクリックします。設定が正しければ緑色の「Success」が表示されます。

## 4. 接続テスト (SQL Explorer)
設定した接続を使って、実際に ClickHouse からデータを取得できるかテストします。

1. 上部メニューの **Data Lab > SQL Explorer** を開きます。
2. 画面左上の **Connection** プルダウンから、作成した `clickhouse_cloud` を選択します。
3. エディタ部分に以下のテストクエリ（ClickHouse のシステムテーブルを取得）を入力します。
   ```sql
   SELECT * FROM system.tables LIMIT 10
   ```
4. 緑色の **[Execute SQL]** ボタンをクリックします。
5. 画面下部にクエリ結果の表が表示されれば、接続テストは完了です！
