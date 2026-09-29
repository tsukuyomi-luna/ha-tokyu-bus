# Tokyu Bus for Home Assistant (unofficial prototype)

東急バスの接近情報を Home Assistant に表示する実験的カスタム連携。
東急の公式・公認連携ではありません。アプリ用の非公開仕様のAPIに依存し、変更で動作しなくなる場合があります。

## 状態

実験版。HA 2026.9.3で設定フロー・センサー4個・再読込を確認済み。
HACSの標準一覧への掲載申請とは別です。

## センサー

- Arrival estimate: APIの到着見込み（分）。時刻表との差ではありません。
- Congestion: LOW / NORMAL / HIGH / UNCLEAR / UNKNOWN。未知を空いていると扱いません。
- Next stop: 同じ便・周回の追跡結果で NEXT の停留所。
- Scheduled departure: 指定した内部系統の次の予定発車時刻（Asia/Tokyo）。追跡車両と同一便だとは扱いません。

`buses` 属性に最大10件、`stops` に順番付き追跡停留所を格納します。車両のGPS座標ではありません。
`retrieved_at` は取得時刻で、事業者の観測時刻ではありません。
API失敗時は接近センサーを unavailable にします。運行データが空なら unknown で、運休とは断定しません。

## HACS（カスタムリポジトリ）

HACS → カスタムリポジトリへ `https://github.com/tsukuyomi-luna/ha-tokyu-bus` を種類「Integration」で追加しダウンロード。HAを再起動後、統合を追加してください。

## 手動導入

`custom_components/tokyu_bus` をHAのconfig/custom_componentsへ配置して再起動。
設定 → デバイスとサービス → 統合を追加 → Tokyu Bus。

現在の設定画面は上級者向けのコード入力です。乗車・降車停留所、内部系統コード、乗り場、UP/DOWNを指定。
表示系統番号（表示名）と内部コードは別。空の応答で接続成功しても区間の妥当性は保証しません。
名前検索UI、options/reconfigureは未実装です。変更時はエントリを削除し再登録してください。

更新は既定5分、最短2分。全センサーで接近取得を共有、先頭便だけ追跡。時刻表は日付・曜日種別でキャッシュ。
この間隔は提供元が公認するレートではありません。大量登録・短時間の更新連打はしないでください。

時刻表は日本の通常平日・土曜・日曜祝日を判定。臨時ダイヤや年末年始・お盆の特別運用は未対応。
同じ表示系統にも複数内部コードがあり、指定コード以外の便は含みません。全便と誤解しないでください。

## 表示

`examples/dashboard.yaml` をカードのYAMLへ貼り、実際のentity_idに置換。
`examples/live-activity.yaml` は手動実行するscriptの例です。iPhoneへの自動送信は勝手に有効化しません。
時刻表のカウントダウンと実車接近は別情報です。iOSではタイマーが本文を置き換えるため、混雑・位置との同時表示は実機調整が必要です。

## 開発

`python3 -m unittest discover -s tests -v`

解析したAPK、逆コンパイルコード、認証情報、個人の通勤設定は同梱していません。

参考: [HACS](https://www.hacs.xyz/docs/publish/integration/), [HA coordinator](https://developers.home-assistant.io/docs/integration_fetching_data/), [Live Activities](https://companion.home-assistant.io/docs/notifications/live-activities/)
