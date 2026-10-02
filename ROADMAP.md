# Roadmap

What's built (M1, M2, half of M3) and the candidates for later milestones, grouped by theme. Sources in parentheses; all are free and keyless unless marked.

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

## M3: solar system depth

- ✅ `get_jupiter_moons`, `get_jupiter_events`: Galilean moon positions, transits, shadow transits, occultations, eclipses and GRS transit times (offline). Event times are for the moon's centre, good to a few minutes. The Red Spot's longitude is a constant with a drift rate in `jupiter.py` (91° on 2026-06-01, +1.75°/month, from Sky & Telescope / JUPOS) and needs a yearly update; tools take an override.
  - Still open: mutual events between the moons, and fetching the Red Spot's longitude from JUPOS.
- ✅ `get_lunar_terminator`: named features in low sunlight on the terminator (USGS planetary nomenclature, downloaded once). Lettered satellite craters are left out.
- ✅ `get_moon_libration`: libration angles, favoured limb, and how 45 limb features are placed and lit (offline, topocentric with a location).
- ✅ `find_conjunctions`, `find_oppositions`: closest approaches between planets (optionally the Moon), and outer-planet oppositions with closest approach to Earth (offline).
  - Still open: planet-star conjunctions, greatest elongations of Mercury and Venus.
- `get_comet_visibility`, `get_asteroid_ephemeris`: bright comets and asteroids (JPL Horizons, MPC, COBS).
- `find_close_approaches`, `get_fireball_reports`: NEO passes and bolides (JPL SBDB CAD, CNEOS).

## M4: satellites

- `get_iss_passes`, `get_satellite_passes`: visible passes with brightness (CelesTrak TLEs + sgp4 or Skyfield).
- `find_satellites_overhead`, `get_starlink_trains`: what's up right now.
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
