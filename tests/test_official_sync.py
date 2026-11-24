#!/usr/bin/env python3
import sys,unittest
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/"scripts"))
from sync_hoyolab_official import eligible,extract,merge
class OfficialSyncTests(unittest.TestCase):
 def setUp(self):
  self.rule={"uid":"172534910","certification_desc":"HonkaiSR Official"}
  self.post={"文章ID":"47385253","網址":"https://www.hoyolab.com/article/47385253","標題":"4.7版本活動躍遷","發文者UID":"172534910","官方欄位":{"user_certification":{"desc":"HonkaiSR Official"}}}
 def test_whitelist(self):
  self.assertTrue(eligible(self.post,self.rule))
  self.assertFalse(eligible({**self.post,"發文者UID":"999"},self.rule))
  self.assertFalse(eligible({**self.post,"官方欄位":{}},self.rule))
 def test_preserve_fields(self):
  old={"games":[{"id":"hsr","current":"4.6","phases":[{"characters":"原有資料"}],"official_announcements":[]}]}
  updated=merge(old,[extract(self.post)],"hsr","2026-11-24T00:00:00+00:00")
  self.assertEqual(updated["current"],"4.6")
  self.assertEqual(len(updated["phases"]),1)
  self.assertEqual(updated["official_announcements"][0]["version"],"4.7")
 def test_reject_untrusted_url(self):
  bad={**extract(self.post),"url":"https://example.com/article/47385253"}
  self.assertNotIn("official_announcements",merge({"games":[]} ,[bad],"hsr","now"))
if __name__=="__main__":unittest.main()
