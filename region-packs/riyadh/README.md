# Riyadh region pack

Eleven heritage sites in the Riyadh region, two of them UNESCO World Heritage properties (`building_type: world_heritage`, which raises their priority in satellite screening). It replaces the earlier `diriyah` pack; At-Turaif keeps its slug and boundary.

Every coordinate below was copied from the cited page. **All boundaries except At-Turaif's area are approximations**: circles sized by building type around the cited point. Replace them with surveyed boundaries from the Heritage Commission before any real decision rests on them. No site has facades or baseline photos yet ([ADR-023](../../docs/adr/ADR-023-sites-without-facades.md)), so a ground check on a satellite alert tells the inspector a site visit is needed instead of opening visitor photo missions.

| Site | Point (lat, lon) and source | Boundary | Documented threats |
|---|---|---|---|
| حي الطريف في الدرعية (`at-turaif`) | 24.734133, 46.572467 ([UNESCO nomination summary](https://whc.unesco.org/document/168966)) | 28.78 ha, the same 24-sided circle as before (radius 302.7 m) | [Erosion of adobe structures from rare but violent rain storms; flooding risk to lower parts](https://whc.unesco.org/document/152384); [Riyadh urban growth reaching the oasis edge; visitor-centre/museum project pressure on integrity](https://whc.unesco.org/document/152384); [Falling Wadi Hanifah water table from heavy pumping](https://whc.unesco.org/document/152384) |
| المنظر الثقافي لمنطقة الفاو الأثرية (`al-faw`) | 19.764917, 45.163389 ([Wikipedia (Qaryat al-Faw)](https://en.wikipedia.org/wiki/Qaryat_al-Faw)) | Core settlement only, 400 m circle. The inscribed property is 4,847.73 ha (ICOMOS), far larger than one screening window | [Slow natural deterioration of exposed remains (rain, wind erosion, temperature swings, termites)](https://whc.unesco.org/document/208495); [Escarpment collapse burying tumuli and cairns](https://whc.unesco.org/en/decisions/8606); [Farming in the buffer zone and road-traffic impacts](https://whc.unesco.org/en/decisions/8606); [Looting (site fenced against looters)](https://en.wikipedia.org/wiki/Qaryat_al-Faw) |
| قصر المصمك (`masmak`) | 24.631238, 46.713408 ([Archnet](https://archnet.org/sites/3797)) | 45 m circle | None found in public sources (not the same as no risk) |
| قصر المربع (`murabba`) | 24.646519, 46.709286 ([IRCICA Islamic Architectural Heritage database](https://islamicarchitecturalheritage.com/?p=967)) | 80 m circle | None found in public sources (not the same as no risk) |
| قرية أشيقر التراثية (`ushaiqer`) | 25.3425, 45.183333 ([Wikipedia (Ushaiger)](https://en.wikipedia.org/wiki/Ushaiger)) | 300 m circle. The point marks the town to the minute, not the heritage core | [Collapse of old mud houses after heavy rain (16 Muharram 1435 / Nov 2013)](https://www.arabiaweather.com/en/content/%D8%A8%D8%A7%D9%84%D9%81%D9%8A%D8%AF%D9%8A%D9%88-%D9%85%D9%82%D8%B7%D8%B9-%D9%83%D8%A7%D9%85%D9%84-%D9%84%D8%A7%D9%86%D9%87%D9%8A%D8%A7%D8%B1-%D8%A8%D9%8A%D9%88%D8%AA-%D8%A7%D9%84%D8%B7%D9%8A%D9%86-%D8%A7%D9%84%D8%AA%D8%B1%D8%A7%D8%AB%D9%8A%D8%A9-%D9%82%D8%B1%D8%A8-%D8%A7%D9%84%D8%B1%D9%8A%D8%A7%D8%B6-%D8%A8%D8%B9%D8%AF-%D8%A7%D9%84%D8%A3%D9%85%D8%B7%D8%A7%D8%B1) |
| بلدة الغاط القديمة (الديرة) (`al-ghat`) | 26.021389, 45.0 ([IRCICA database](https://islamicarchitecturalheritage.com/?p=978)) | 250 m circle. The longitude is exactly 45°E and looks rounded | None found in public sources (not the same as no risk) |
| قرية سدوس التراثية (`sudus`) | 24.993867, 46.207658 ([IRCICA database (matches GeoNames 101816)](https://islamicarchitecturalheritage.com/?p=2242)) | 150 m circle | [Partial demolition of parts of the historic village fabric](https://islamicarchitecturalheritage.com/?p=2242) |
| قصر الملك عبدالعزيز بالدوادمي (`dawadmi-palace`) | 24.481667, 44.360833 ([IRCICA database](https://islamicarchitecturalheritage.com/?p=968)) | 50 m circle | None found in public sources (not the same as no risk) |
| قصر الملك عبدالعزيز التاريخي بالخرج (`kharj-palace`) | 24.151944, 47.2975 ([IRCICA database](https://islamicarchitecturalheritage.com/?p=969)) | 60 m circle | None found in public sources (not the same as no risk) |
| قصر الإمارة القديم (قصر الملك عبدالعزيز) بوادي الدواسر (`wadi-dawasir-palace`) | 20.473911, 44.790719 ([IRCICA database](https://www.islamicarchitecturalheritage.com/?p=2256)) | 50 m circle | [Poor condition; most internal elements destroyed (restoration begun)](https://www.islamicarchitecturalheritage.com/?p=2256) |
| موقع المقر الأثري (`al-magar`) | 19.744213, 44.620447 ([Wikipedia (Al-Magar)](https://en.wikipedia.org/wiki/Al-Magar)) | 300 m circle. Governorate between Wadi al-Dawasir and Tathlith is uncertain | None found in public sources (not the same as no risk) |

## Sites left out

These sites matter but had no citable coordinate when the pack was built: Al-Bujairi and Ghasiba in Diriyah, Qasr Salma in Al-Aflaj (wall sections fell in the July 2021 flood), Shaqra heritage village (two conflicting city points), the Al-Yamama mosque excavation in Al-Kharj, the Tuwaiq stone trails such as Darb Aba al-Qudd, and Abu Jifan Fort (only a blog's map pin). Add them once a Wikidata, OpenStreetMap or Heritage Commission point is available.

## Sample events

`sample-events.json` holds **invented** changes (new construction near At-Turaif, standing water in Ushaiqer, digging in Sudus, sand near Al-Faw, palm loss near the Al-Kharj palace). It feeds the sample scene source (`SADU_SCENE_SOURCE=sample`) for demos and tests when Sentinel-2 is out of reach. The dashboard labels every scan from it as sample data. None of these events was observed.

## Import

```
docker compose exec api python -m sadu.cli seed --pack riyadh
```
