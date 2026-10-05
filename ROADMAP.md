# Roadmap

What's built (M1 to M3, half of M4) and the candidates for later milestones, grouped by theme. Sources in parentheses; all are free and keyless unless marked.

## M1: tonight's sky (done)

`set_default_location`, `geocode_location`, `describe_object`, `search_deep_sky`, `identify_constellation`, `get_position`, `get_rise_set_transit`, `get_twilight_times`, `get_moon_phases`, `get_planet_positions`, `whats_up_tonight`, `is_visible_tonight`, `get_sky_forecast`, `get_limiting_magnitude`, `get_eclipses`, `get_space_weather`, `get_upcoming_launches`.

Gaps found in M1, now closed:

- ✅ **Light pollution was user-supplied.** Sky brightness now comes from the 2025 Light Pollution Atlas (VIIRS-based) via `get_light_pollution`. A Bortle class or SQM reading from the user still takes priority.
- ✅ **Visibility heuristics were uncalibrated.** They're replaced by a detection-threshold model (`visibility.py`) and a Krisciunas & Schaefer moonlight profile, tuned against a 53-case benchmark from Bortle's published descriptions and standard observing experience. It passes all 53 cases.
  - Still open: calibrating against real observing logs. That needs `log_observation` (M7) so outcomes can be compared with predictions.
- ✅ **Terrain was ignored.** `whats_up_tonight` and `is_visible_tonight` now apply a cached terrain horizon profile.

## M2: conditions and site (done)

- ✅ `get_light_pollution`: atlas zone, SQM, estimated Bortle and naked-eye limit at a coordinate (Light Pollution Atlas 2025 tiles).
- ✅ `find_dark_sites`: darkest, then nearest, spots within a radius, each with OpenStreetMap access points. Distances are straight-line; driving time would need a routing service.
- ✅ `get_horizon_profile`: terrain horizon from Copernicus DEM (Open-Meteo), with OpenTopoData as fallback.
- ✅ `get_transparency_drivers`: smoke, dust and aerosols over a night, with a rating and the extra extinction (Open-Meteo Air Quality, about 5 days ahead). The named driver is a heuristic: the model can't separate smoke from urban haze.
- ✅ `best_night_this_month`: scores upcoming nights on usable time, target altitude, moonlight near the target and cloud forecast. Nights past the 16-day cloud forecast are ranked separately. Terrain is not applied.
- ✅ `find_dark_moon_weekends`: Friday and Saturday nights with the Moon down for most of the dark hours (offline).

## M3: solar system depth (done)

- ✅ `get_jupiter_moons`, `get_jupiter_events`: Galilean moon positions, transits, shadow transits, occultations, eclipses and GRS transit times (offline). Event times are for the moon's centre, good to a few minutes. The Red Spot's longitude is a constant with a drift rate in `jupiter.py` (91° on 2026-06-01, +1.75°/month, from Sky & Telescope / JUPOS) and needs a yearly update; tools take an override.
  - Still open: mutual events between the moons, and fetching the Red Spot's longitude from JUPOS.
- ✅ `get_lunar_terminator`: named features in low sunlight on the terminator (USGS planetary nomenclature, downloaded once). Lettered satellite craters are left out.
- ✅ `get_moon_libration`: libration angles, favoured limb, and how 45 limb features are placed and lit (offline, topocentric with a location).
- ✅ `find_conjunctions`, `find_oppositions`: closest approaches between planets (optionally the Moon), and outer-planet oppositions with closest approach to Earth (offline).
  - Still open: planet-star conjunctions, greatest elongations of Mercury and Venus.
- ✅ `get_comet_visibility`, `get_asteroid_ephemeris`: bright comets now, or one comet's view tonight and its trend, and ephemerides for any comet or asteroid (JPL SBDB and Horizons, COBS). The bright-comet list propagates every comet offline to pick candidates, then takes their positions from Horizons. Brightness is COBS's fit to observer reports where one exists within two years of perihelion, otherwise JPL's M1/K1 prediction.
  - Still open: a list of bright asteroids (Vesta and friends near opposition), and COBS's own recent observations rather than its fitted magnitude. The MPC isn't used: SBDB and Horizons cover the same objects.
- ✅ `find_close_approaches`, `get_fireball_reports`: NEO passes with size estimates, and bolides with distance and whether they were above the observer's horizon (JPL SBDB CAD, CNEOS).
  - Still open: ordinary bright-meteor reports (the AMS and IMO fireball databases need keys or scraping).

## M4: satellites

- ✅ `get_iss_passes`, `get_satellite_passes`: visible passes with appear, peak and vanish points and an estimated magnitude (CelesTrak GP elements, sgp4). Checked against Skyfield: positions agree to under an arcminute and rise times to about a second. Earth's shadow is a cylinder, so fade times can be off by a few seconds.
  - Still open: standard magnitudes for more satellites. Only the ISS, Tiangong, Hubble and Starlink have built-in values, since McCants' list is no longer online; others take `standard_magnitude` from the caller.
- ✅ `find_satellites_overhead`, `get_starlink_trains`: what's up now and where it's heading, and recent Starlink batches with how stretched out each train is and when it passes.
  - Still open: batches CelesTrak hasn't named yet (the first day or so after launch) are missed; matching them to Launch Library launches would catch them.
- `predict_iss_transit`: ISS crossing the Sun or Moon from a site.
- `get_dsn_status`: which spacecraft the Deep Space Network is talking to (DSN Now XML).

## M5: stars, variables, transients, exoplanets

- `get_double_star`, `find_splittable_doubles`: WDS via VizieR, matched to aperture and seeing.
- `get_variable_star_status`, `get_light_curve`: AAVSO observations, ASAS-SN Sky Patrol.
- `get_recent_supernovae`, `get_novae`: TNS (free key), ALeRCE / Fink brokers.
- `get_exoplanet`, `search_exoplanets`, `get_transits_tonight`: NASA Exoplanet Archive TAP.
- `get_gravitational_wave_events`: GWOSC / GraceDB.

## M6: astrophotography and charts

- `calculate_field_of_view`, `frame_target`, `plan_mosaic`: optics math plus catalog sizes.
- `calculate_exposure`: NPF rule for untracked shots.
- `plan_milky_way_shot`: galactic core position and timing.
- `get_survey_cutout`, `generate_finder_chart`: DSS / Pan-STARRS cutouts (SkyView, hips2fits).
- `plate_solve_image`: Astrometry.net (free key).

## M7: sessions and personalisation

- `plan_observing_session`, `optimize_target_order`: an ordered schedule under altitude and time limits.
- `plan_messier_marathon`: the ordering problem for the one night a year it works.
- `log_observation`, `get_observing_history`, `get_catalog_progress`, `suggest_unobserved`.
- `save_equipment_profile`: telescopes, eyepieces and cameras as reusable context.
- `export_to_telescope`: SkySafari / NINA target lists.

## Reference and outreach

- `get_apod`, `get_mission_info`, `get_astronauts_in_space`, `get_space_news` (api.nasa.gov key, Spaceflight News API).
- `search_literature`, `get_recent_papers` (NASA ADS key, arXiv).
- `get_constellation_story`: sky cultures from Stellarium data files.
- `get_meteor_showers`, `get_shower_conditions`: IMO calendar plus radiant altitude and moonlight.

## MCP beyond tools

- **Resources:** the bundled catalog, saved sites and equipment, and generated charts.
- **Prompts:** "plan tonight", "identify what I saw", "plan an imaging project".
- **Elicitation:** ask for location or equipment mid-call instead of erroring.
