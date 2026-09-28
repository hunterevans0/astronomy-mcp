# Roadmap

What's built (M1) and the candidates for later milestones, grouped by theme. Sources in parentheses; all are free and keyless unless marked.

## M1: tonight's sky (done)

`set_default_location`, `geocode_location`, `describe_object`, `search_deep_sky`, `identify_constellation`, `get_position`, `get_rise_set_transit`, `get_twilight_times`, `get_moon_phases`, `get_planet_positions`, `whats_up_tonight`, `is_visible_tonight`, `get_sky_forecast`, `get_limiting_magnitude`, `get_eclipses`, `get_space_weather`, `get_upcoming_launches`.

Known gaps in M1:

- **Light pollution is user-supplied.** Bortle is entered, not looked up. Sampling the VIIRS or Falchi 2016 rasters would make `get_light_pollution` automatic.
- **Visibility heuristics are uncalibrated.** Surface-brightness and moon-separation rules are rough and should be tuned against real observing logs.
- **Terrain is ignored.** There's no horizon profile, so targets behind a ridge still get recommended (see `get_horizon_profile` in M2).

## M2: conditions and site

- `get_light_pollution`: Bortle, SQM and naked-eye limit at a coordinate (VIIRS / Falchi raster, bulk).
- `find_dark_sites`: darkest reachable spots within a drive radius (raster + OSM Overpass).
- `get_horizon_profile`: terrain horizon from a DEM (OpenTopoData / Copernicus DEM).
- `get_transparency_drivers`: smoke, dust and aerosols (Open-Meteo Air Quality).
- `best_night_this_month`: score upcoming nights on moon, target altitude and forecast.
- `find_dark_moon_weekends`: new-moon weekends for trip planning (offline).

## M3: solar system depth

- `get_jupiter_moons`, `get_jupiter_events`: Galilean moon positions, transits, shadow transits, GRS transit times.
- `get_lunar_terminator`: craters on the terminator tonight (USGS planetary nomenclature).
- `get_moon_libration`: which limb features are visible (offline).
- `find_conjunctions`, `find_oppositions`: planetary events over a date range (offline).
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
