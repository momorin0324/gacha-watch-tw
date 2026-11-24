import datetime,sys,unittest
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/"scripts"))
from advance_versions import advance
UTC=datetime.timezone.utc
def v(name,start,end):
 return {"version":name,"start":start,"end":end,"verified":True,"source":"https://example.org/official","phases":[{"characters":["Example"]}]}
class VersionRolloverTests(unittest.TestCase):
 def setUp(self):
  self.now=datetime.datetime(2026,12,1,tzinfo=UTC)
 def test_archive_and_promote(self):
  doc={"games":[{"id":"hsr","current_version":v("4.6","2026-10-01T00:00:00Z","2026-11-30T00:00:00Z"),"next_version":v("4.7","2026-11-30T00:00:00Z","2027-01-01T00:00:00Z"),"official_announcements":[1]}],"history":[]}
  out,changed=advance(doc,self.now)
  self.assertTrue(changed)
  self.assertEqual(out["games"][0]["current_version"]["version"],"4.7")
  self.assertIsNone(out["games"][0]["next_version"])
  self.assertEqual(out["history"][0]["version"],"4.6")
  self.assertEqual(out["games"][0]["official_announcements"],[1])
  again,changed=advance(out,self.now)
  self.assertFalse(changed)
  self.assertEqual(len(again["history"]),1)
 def test_unverified_not_promoted(self):
  candidate=v("4.7","2026-11-30T00:00:00Z","2027-01-01T00:00:00Z")
  candidate["verified"]=False
  doc={"games":[{"id":"hsr","next_version":candidate}],"history":[]}
  out,changed=advance(doc,self.now)
  self.assertFalse(changed)
 def test_missing_timezone_not_promoted(self):
  candidate=v("4.7","2026-11-30T00:00:00","2027-01-01T00:00:00")
  out,changed=advance({"games":[{"id":"hsr","next_version":candidate}]},self.now)
  self.assertFalse(changed)
if __name__=="__main__":unittest.main()
