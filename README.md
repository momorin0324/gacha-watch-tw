# Gacha Watch TW — 官方公告快速同步（第一階段）

## 每日自動更新
- GitHub Actions: `.github/workflows/sync.yml`，每天台灣時間 **08:00、20:00**（UTC 00:00、12:00），可手動執行。
- `scripts/sync_hoyolab_official.py` 從 HoYoLAB 公開 API 擷取原神、崩壞：星穹鐵道、絕區零最近 20 篇公告。
- `config/official_accounts.json` 設定官方 UID + 認證描述雙重白名單。認證不符或抓取失敗不會覆蓋舊資料。
- 目前已自動寫入 `data/updates.json` 的欄位：`official_announcements`（公告標題、網址、分類、版本提示）、`latest_official_version_announcement`（**僅是最新版本公告，不等同目前遊戲版本**）。
- 同步狀態在 `data/sync_status.json`。GitHub Pages 在資料 commit 後由 `pages.yml` 重新部署。
- 舊的可信結構化 JSON 同步 `scripts/sync.py` 仍保留，不會刪除新公告欄位。

## 尚未完成
- **角色／裝備 UP 名單、卡池起訖時間、前瞻直播精確時間、歷史卡池正式自動發布** 尚未接入；沒有官方證據時不會猜測。
- 前端是否顯示 `official_announcements` 需另外確認和整合；目前保證的是 JSON 資料自動更新，不等於每個畫面都已顯示。
- GitHub Actions 定時工作可能延遲，不能保證嚴格在 24 小時內更新。
- HoYoLAB API 欄位與官方帳號認證可能變更；需要首輪實跑檢查白名單。
- 既有 `config/sources.json` 仍是空的，供另外的可信 JSON feed 使用，不影響新的官方公告抓取。

## 驗證
```bash
python -m unittest discover -s tests -p 'test_official_sync.py'
python scripts/sync_hoyolab_official.py
```

<!-- Trigger a fresh GitHub Pages deployment. -->
