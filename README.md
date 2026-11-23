# Gacha Watch TW v132 — 自動同步基礎版

## 部署
1. 將整個資料夾（包含隱藏的 `.github`）上傳至 GitHub repository 的 `main` 分支。
2. GitHub Settings → Pages → Source 選擇 **GitHub Actions**。
3. `Publish Gacha Watch` 會部署網站。`Gacha Watch verified sync` 每小時第 17 分執行，亦可手動觸發。

## 重要：尚未接入 11 款官方公告
`config/sources.json` 目前為空。這不是已完成的官方自動爬蟲；**沒有官方公告被自動抓取**。只有新增經核實的、支援 JSON schema 的可信來源後，才會同步新資料。官方公告多為 HTML、圖片、直播，需針對每款遊戲開發解析器及驗證規則，不能直接把未經核實文字當卡池事實。

## 同步安全
- 原始 v131 靜態資料內嵌在 HTML 中，更新資料在 `data/updates.json`，不會刪除舊資料。
- 同步資料只接受 `verified: true` 的紀錄；每個 phase 需要角色、帶時區的 ISO 開始及結束時間、HTTPS 來源。
- 若同步失敗，保留上次已驗證資料；瀏覽器離線開啟 HTML 時使用內建快照。
- 目前新增的已核實資料會合併到前端，既有當期卡池的移轉仍依現有 `verifiedHistory` 日期邏輯；完整的跨版本自動遷移仍需要對舊資料結構做進一步整合。

## JSON feed 格式範例（僅格式，非真實卡池）
```json
{"schema":1,"games":[{"id":"genshin","verified":true,"evidence_url":"https://example.org/official-announcement","current":"X.Y","phases":[{"characters":"示例角色","start":"2027-01-01T10:00:00+08:00","end":"2027-01-20T17:59:00+08:00","source":"https://example.org/official-announcement"}]}],"history":[]}
```
**此範例不應當作正式資料發布。**
