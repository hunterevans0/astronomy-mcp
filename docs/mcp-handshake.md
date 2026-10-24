# astronomy MCP server: `initialize` and `tools/list` responses

Captured 2026-10-22 by launching `python -m astronomy_mcp` over stdio and sending raw JSON-RPC. Nothing was added or removed; the pretty-printed blocks only re-indent the exact line the server wrote.

Sequence: `initialize` → `notifications/initialized` (no response) → `tools/list`.

## 1. `initialize`

### Request (client → server)

```json
{
  "jsonrpc": "2.0",
  "id": 1,
  "method": "initialize",
  "params": {
    "protocolVersion": "2025-11-25",
    "capabilities": {},
    "clientInfo": {
      "name": "probe",
      "version": "0"
    }
  }
}
```

### Response (server → client), pretty-printed

```json
{
  "jsonrpc": "2.0",
  "id": 1,
  "result": {
    "capabilities": {
      "experimental": {},
      "prompts": {
        "listChanged": false
      },
      "resources": {
        "listChanged": false,
        "subscribe": false
      },
      "tools": {
        "listChanged": false
      }
    },
    "instructions": "Tools for observational astronomy: what is in the sky from a given place and time, whether and when something can be seen, observing conditions (clouds, darkness, light pollution, terrain), sourced catalog facts about celestial objects, comets, asteroids, satellites, eclipses, space weather and rocket launches.\n\nWhen an answer depends on the date, time or the observer's location (what is up tonight, where a planet is, rise/set or twilight times, Moon phase, whether an object is visible, the cloud forecast, how dark a site is), prefer calling a tool over answering from memory: these values change daily and by location, and recalled numbers are often wrong. For catalog facts such as magnitudes, sizes, distances and variability, the tools return sourced values; use them when the specific numbers matter.\n\nQuestions about general astronomy knowledge, history, physics, or how to use equipment do not need these tools; answer those directly.\n\nRouting: 'what should I look at tonight' -> whats_up_tonight; 'can I see X' -> is_visible_tonight; 'will it be clear' -> get_sky_forecast; 'is it smoky or hazy' -> get_transparency_drivers; 'which night is best' -> best_night_this_month; 'when is the next new-moon weekend' -> find_dark_moon_weekends; 'how dark is it here' -> get_light_pollution; 'where can I go for darker skies' -> find_dark_sites; 'tell me about X' -> describe_object; planet positions -> get_planet_positions; Moon phases -> get_moon_phases; Jupiter's moons or Red Spot -> get_jupiter_moons, get_jupiter_events; what to look at on the Moon -> get_lunar_terminator, get_moon_libration; planets close together or at their best -> find_conjunctions, find_oppositions; Mercury or Venus at their best -> find_greatest_elongations; asteroids to look for -> find_bright_asteroids; ISS crossing the Sun or Moon -> predict_iss_transit; comets -> get_comet_visibility; where an asteroid or comet is -> get_asteroid_ephemeris; asteroids passing Earth -> find_close_approaches; bolides -> get_fireball_reports; ISS sightings -> get_iss_passes; other satellites -> get_satellite_passes; 'what is that moving light' -> find_satellites_overhead; Starlink trains -> get_starlink_trains; double stars -> get_double_star, find_splittable_doubles; how a variable star is doing -> get_variable_star_status, get_light_curve; supernovae -> get_recent_supernovae; novae -> get_novae; which spacecraft NASA is talking to -> get_dsn_status; exoplanets -> get_exoplanet, search_exoplanets, get_transits_tonight; gravitational waves -> get_gravitational_wave_events; camera or eyepiece field of view -> calculate_field_of_view; will a target fit -> frame_target, plan_mosaic; untracked exposure length -> calculate_exposure; Milky Way core photos -> plan_milky_way_shot; a survey image of a field -> get_survey_cutout; a chart for finding a target -> generate_finder_chart; where a photo points or what is in it -> plate_solve_image; aurora -> get_space_weather; launches -> get_upcoming_launches.\n\nLocation: tools take latitude/longitude or a place name, and otherwise use the saved default. When the user says where they observe from, call set_default_location once. If no location is known and the question needs one, ask the user.\n\nIf a tool finds no match or a service is unavailable, say so rather than substituting remembered values. Visibility verdicts, sky brightness and limiting magnitudes are model estimates; present them that way. Times come back in the observer's local time with a UTC offset; coordinates are ICRS/J2000 degrees.",
    "protocolVersion": "2025-11-25",
    "serverInfo": {
      "name": "astronomy",
      "title": "Astronomy Data",
      "version": "0.3.0"
    }
  }
}
```

### Response, exact bytes on the wire (3858 bytes, one line)

```json
{"jsonrpc":"2.0","id":1,"result":{"capabilities":{"experimental":{},"prompts":{"listChanged":false},"resources":{"listChanged":false,"subscribe":false},"tools":{"listChanged":false}},"instructions":"Tools for observational astronomy: what is in the sky from a given place and time, whether and when something can be seen, observing conditions (clouds, darkness, light pollution, terrain), sourced catalog facts about celestial objects, comets, asteroids, satellites, eclipses, space weather and rocket launches.\n\nWhen an answer depends on the date, time or the observer's location (what is up tonight, where a planet is, rise/set or twilight times, Moon phase, whether an object is visible, the cloud forecast, how dark a site is), prefer calling a tool over answering from memory: these values change daily and by location, and recalled numbers are often wrong. For catalog facts such as magnitudes, sizes, distances and variability, the tools return sourced values; use them when the specific numbers matter.\n\nQuestions about general astronomy knowledge, history, physics, or how to use equipment do not need these tools; answer those directly.\n\nRouting: 'what should I look at tonight' -> whats_up_tonight; 'can I see X' -> is_visible_tonight; 'will it be clear' -> get_sky_forecast; 'is it smoky or hazy' -> get_transparency_drivers; 'which night is best' -> best_night_this_month; 'when is the next new-moon weekend' -> find_dark_moon_weekends; 'how dark is it here' -> get_light_pollution; 'where can I go for darker skies' -> find_dark_sites; 'tell me about X' -> describe_object; planet positions -> get_planet_positions; Moon phases -> get_moon_phases; Jupiter's moons or Red Spot -> get_jupiter_moons, get_jupiter_events; what to look at on the Moon -> get_lunar_terminator, get_moon_libration; planets close together or at their best -> find_conjunctions, find_oppositions; Mercury or Venus at their best -> find_greatest_elongations; asteroids to look for -> find_bright_asteroids; ISS crossing the Sun or Moon -> predict_iss_transit; comets -> get_comet_visibility; where an asteroid or comet is -> get_asteroid_ephemeris; asteroids passing Earth -> find_close_approaches; bolides -> get_fireball_reports; ISS sightings -> get_iss_passes; other satellites -> get_satellite_passes; 'what is that moving light' -> find_satellites_overhead; Starlink trains -> get_starlink_trains; double stars -> get_double_star, find_splittable_doubles; how a variable star is doing -> get_variable_star_status, get_light_curve; supernovae -> get_recent_supernovae; novae -> get_novae; which spacecraft NASA is talking to -> get_dsn_status; exoplanets -> get_exoplanet, search_exoplanets, get_transits_tonight; gravitational waves -> get_gravitational_wave_events; camera or eyepiece field of view -> calculate_field_of_view; will a target fit -> frame_target, plan_mosaic; untracked exposure length -> calculate_exposure; Milky Way core photos -> plan_milky_way_shot; a survey image of a field -> get_survey_cutout; a chart for finding a target -> generate_finder_chart; where a photo points or what is in it -> plate_solve_image; aurora -> get_space_weather; launches -> get_upcoming_launches.\n\nLocation: tools take latitude/longitude or a place name, and otherwise use the saved default. When the user says where they observe from, call set_default_location once. If no location is known and the question needs one, ask the user.\n\nIf a tool finds no match or a service is unavailable, say so rather than substituting remembered values. Visibility verdicts, sky brightness and limiting magnitudes are model estimates; present them that way. Times come back in the observer's local time with a UTC offset; coordinates are ICRS/J2000 degrees.","protocolVersion":"2025-11-25","serverInfo":{"name":"astronomy","title":"Astronomy Data","version":"0.3.0"}}}
```

## 2. `tools/list`

### Request (client → server)

```json
{
  "jsonrpc": "2.0",
  "id": 2,
  "method": "tools/list"
}
```

### Response (server → client), pretty-printed

```json
{
  "jsonrpc": "2.0",
  "id": 2,
  "result": {
    "tools": [
      {
        "annotations": {
          "idempotentHint": true,
          "openWorldHint": true,
          "readOnlyHint": true
        },
        "description": "Turn a place name into coordinates, elevation and timezone (Open-Meteo geocoder).\n\nUseful when a place is ambiguous and the user should pick; other tools also accept a\nplace name directly.\n",
        "inputSchema": {
          "properties": {
            "query": {
              "description": "Place name, optionally qualified: 'Moab, Utah', 'Cherry Springs State Park'",
              "title": "Query",
              "type": "string"
            },
            "count": {
              "default": 5,
              "description": "Maximum candidates",
              "maximum": 10,
              "minimum": 1,
              "title": "Count",
              "type": "integer"
            }
          },
          "required": [
            "query"
          ],
          "type": "object",
          "title": "geocode_locationArguments"
        },
        "name": "geocode_location",
        "outputSchema": {
          "type": "object",
          "additionalProperties": true,
          "title": "geocode_locationDictOutput"
        }
      },
      {
        "annotations": {
          "destructiveHint": false,
          "idempotentHint": true,
          "openWorldHint": true,
          "readOnlyHint": false
        },
        "description": "Save the observer's default location so later questions don't need it repeated.\n\nCall this when the user tells you where they usually observe from. Only pass bortle if\nthe user states it; otherwise sky darkness comes from the light-pollution atlas, which\nthis call reports. Stored in ~/.astronomy-mcp/config.json across sessions.\n",
        "inputSchema": {
          "properties": {
            "place": {
              "anyOf": [
                {
                  "type": "string"
                },
                {
                  "type": "null"
                }
              ],
              "default": null,
              "description": "Place name to observe from instead of coordinates, e.g. 'Moab, Utah'.",
              "title": "Place"
            },
            "latitude": {
              "anyOf": [
                {
                  "maximum": 90,
                  "minimum": -90,
                  "type": "number"
                },
                {
                  "type": "null"
                }
              ],
              "default": null,
              "description": "Observer latitude in degrees (north positive). Omit to use place or the saved default.",
              "title": "Latitude"
            },
            "longitude": {
              "anyOf": [
                {
                  "maximum": 180,
                  "minimum": -180,
                  "type": "number"
                },
                {
                  "type": "null"
                }
              ],
              "default": null,
              "description": "Observer longitude in degrees (east positive). Omit to use place or the saved default.",
              "title": "Longitude"
            },
            "name": {
              "anyOf": [
                {
                  "type": "string"
                },
                {
                  "type": "null"
                }
              ],
              "default": null,
              "description": "Friendly name to store, e.g. 'Backyard'",
              "title": "Name"
            },
            "bortle": {
              "anyOf": [
                {
                  "maximum": 9,
                  "minimum": 1,
                  "type": "integer"
                },
                {
                  "type": "null"
                }
              ],
              "default": null,
              "description": "Bortle class of the sky (1 pristine to 9 inner city). Omit to use the saved value or the light-pollution atlas.",
              "title": "Bortle"
            }
          },
          "type": "object",
          "title": "set_default_locationArguments"
        },
        "name": "set_default_location",
        "outputSchema": {
          "type": "object",
          "additionalProperties": true,
          "title": "set_default_locationDictOutput"
        }
      },
      {
        "annotations": {
          "idempotentHint": true,
          "openWorldHint": true,
          "readOnlyHint": true
        },
        "description": "Show the saved default observing location, if any.",
        "inputSchema": {
          "properties": {},
          "type": "object",
          "title": "get_default_locationArguments"
        },
        "name": "get_default_location",
        "outputSchema": {
          "type": "object",
          "additionalProperties": true,
          "title": "get_default_locationDictOutput"
        }
      },
      {
        "annotations": {
          "idempotentHint": true,
          "openWorldHint": true,
          "readOnlyHint": true
        },
        "description": "Look up a celestial object in SIMBAD by name or catalog identifier.\n\nReturns coordinates, object type, spectral/morphological type, parallax (and derived\ndistance), proper motion, radial velocity, redshift, multi-band magnitudes and aliases.\ndescribe_object is usually the better first call; use this for raw SIMBAD data.\n",
        "inputSchema": {
          "properties": {
            "identifier": {
              "description": "Any SIMBAD identifier or common name, e.g. 'M31', 'Betelgeuse', 'HD 39801', 'NGC 1976'",
              "title": "Identifier",
              "type": "string"
            }
          },
          "required": [
            "identifier"
          ],
          "type": "object",
          "title": "simbad_lookupArguments"
        },
        "name": "simbad_lookup",
        "outputSchema": {
          "type": "object",
          "additionalProperties": true,
          "title": "simbad_lookupDictOutput"
        }
      },
      {
        "annotations": {
          "idempotentHint": true,
          "openWorldHint": true,
          "readOnlyHint": true
        },
        "description": "Find SIMBAD objects within a radius of a sky position, sorted nearest first.\n\nFor questions like 'what is at these coordinates' or 'what else is near this object'.\n",
        "inputSchema": {
          "properties": {
            "ra_deg": {
              "description": "Right ascension, decimal degrees (ICRS/J2000)",
              "exclusiveMaximum": 360,
              "minimum": 0,
              "title": "Ra Deg",
              "type": "number"
            },
            "dec_deg": {
              "description": "Declination, decimal degrees (ICRS/J2000)",
              "maximum": 90,
              "minimum": -90,
              "title": "Dec Deg",
              "type": "number"
            },
            "radius_arcmin": {
              "default": 5.0,
              "description": "Search radius in arcminutes (max 60)",
              "exclusiveMinimum": 0,
              "maximum": 60,
              "title": "Radius Arcmin",
              "type": "number"
            },
            "object_type": {
              "anyOf": [
                {
                  "type": "string"
                },
                {
                  "type": "null"
                }
              ],
              "default": null,
              "description": "Optional SIMBAD object-type code to filter on, e.g. '*' (star), 'G' (galaxy), 'QSO', 'PN', 'OpC', 'V*' (variable star), 'EB*'",
              "title": "Object Type"
            },
            "max_v_mag": {
              "anyOf": [
                {
                  "type": "number"
                },
                {
                  "type": "null"
                }
              ],
              "default": null,
              "description": "Only return objects with V magnitude at or brighter than this",
              "title": "Max V Mag"
            },
            "limit": {
              "default": 20,
              "description": "Maximum number of results",
              "maximum": 200,
              "minimum": 1,
              "title": "Limit",
              "type": "integer"
            }
          },
          "required": [
            "ra_deg",
            "dec_deg"
          ],
          "type": "object",
          "title": "simbad_cone_searchArguments"
        },
        "name": "simbad_cone_search",
        "outputSchema": {
          "type": "object",
          "additionalProperties": true,
          "title": "simbad_cone_searchDictOutput"
        }
      },
      {
        "annotations": {
          "idempotentHint": true,
          "openWorldHint": true,
          "readOnlyHint": true
        },
        "description": "Look up a variable star in the AAVSO International Variable Star Index (VSX).\n\nReturns variability type, period, epoch, magnitude range, spectral type, discoverer,\nconstellation and a link to the VSX detail page. Use for periods and brightness ranges\nof variable stars rather than recalling them.\n",
        "inputSchema": {
          "properties": {
            "name": {
              "description": "Variable star name, e.g. 'R Leo', 'Mira', 'SS Cyg', 'delta Cep'",
              "title": "Name",
              "type": "string"
            }
          },
          "required": [
            "name"
          ],
          "type": "object",
          "title": "vsx_lookupArguments"
        },
        "name": "vsx_lookup",
        "outputSchema": {
          "type": "object",
          "additionalProperties": true,
          "title": "vsx_lookupDictOutput"
        }
      },
      {
        "annotations": {
          "idempotentHint": true,
          "openWorldHint": true,
          "readOnlyHint": true
        },
        "description": "Find known variable stars in VSX within a radius of a sky position, nearest first.",
        "inputSchema": {
          "properties": {
            "ra_deg": {
              "description": "Right ascension, decimal degrees (ICRS/J2000)",
              "exclusiveMaximum": 360,
              "minimum": 0,
              "title": "Ra Deg",
              "type": "number"
            },
            "dec_deg": {
              "description": "Declination, decimal degrees (ICRS/J2000)",
              "maximum": 90,
              "minimum": -90,
              "title": "Dec Deg",
              "type": "number"
            },
            "radius_deg": {
              "default": 0.5,
              "description": "Search radius in degrees (max 5)",
              "exclusiveMinimum": 0,
              "maximum": 5,
              "title": "Radius Deg",
              "type": "number"
            },
            "max_mag": {
              "anyOf": [
                {
                  "type": "number"
                },
                {
                  "type": "null"
                }
              ],
              "default": null,
              "description": "Only return stars reaching this magnitude or brighter at maximum",
              "title": "Max Mag"
            },
            "limit": {
              "default": 25,
              "description": "Maximum number of results",
              "maximum": 500,
              "minimum": 1,
              "title": "Limit",
              "type": "integer"
            }
          },
          "required": [
            "ra_deg",
            "dec_deg"
          ],
          "type": "object",
          "title": "vsx_cone_searchArguments"
        },
        "name": "vsx_cone_search",
        "outputSchema": {
          "type": "object",
          "additionalProperties": true,
          "title": "vsx_cone_searchDictOutput"
        }
      },
      {
        "annotations": {
          "idempotentHint": true,
          "openWorldHint": true,
          "readOnlyHint": true
        },
        "description": "Resolve a target name with SIMBAD, then list VSX variable stars around it.",
        "inputSchema": {
          "properties": {
            "target": {
              "description": "Name of any object SIMBAD can resolve, e.g. 'M13', 'Vega', 'Pleiades'",
              "title": "Target",
              "type": "string"
            },
            "radius_deg": {
              "default": 0.5,
              "description": "Search radius in degrees (max 5)",
              "exclusiveMinimum": 0,
              "maximum": 5,
              "title": "Radius Deg",
              "type": "number"
            },
            "max_mag": {
              "anyOf": [
                {
                  "type": "number"
                },
                {
                  "type": "null"
                }
              ],
              "default": null,
              "description": "Only return stars reaching this magnitude or brighter at maximum",
              "title": "Max Mag"
            },
            "limit": {
              "default": 25,
              "description": "Maximum number of results",
              "maximum": 500,
              "minimum": 1,
              "title": "Limit",
              "type": "integer"
            }
          },
          "required": [
            "target"
          ],
          "type": "object",
          "title": "variable_stars_nearArguments"
        },
        "name": "variable_stars_near",
        "outputSchema": {
          "type": "object",
          "additionalProperties": true,
          "title": "variable_stars_nearDictOutput"
        }
      },
      {
        "annotations": {
          "idempotentHint": true,
          "openWorldHint": true,
          "readOnlyHint": true
        },
        "description": "Sourced profile of a star, galaxy, nebula, cluster or planet: type, coordinates,\nmagnitudes, distance, size, common names, variability and constellation.\n\nA good first call for 'tell me about X' or 'how far/bright/big is X' when specific numbers\nmatter. Merges SIMBAD, OpenNGC and AAVSO VSX; planets get their current apparent details.\n",
        "inputSchema": {
          "properties": {
            "name": {
              "description": "Planet, 'Moon', catalog name (M42, NGC 7000, Caldwell 14), common name (Ring Nebula) or SIMBAD identifier",
              "title": "Name",
              "type": "string"
            }
          },
          "required": [
            "name"
          ],
          "type": "object",
          "title": "describe_objectArguments"
        },
        "name": "describe_object",
        "outputSchema": {
          "type": "object",
          "additionalProperties": true,
          "title": "describe_objectDictOutput"
        }
      },
      {
        "annotations": {
          "idempotentHint": true,
          "openWorldHint": true,
          "readOnlyHint": true
        },
        "description": "Find deep-sky objects by kind, constellation, brightness or size, brightest first.\n\nFor requests like 'bright planetary nebulae', 'Messier objects in Sagittarius' or\n'large galaxies visible tonight'. Covers NGC, IC, Messier and Caldwell extras (OpenNGC).\nFor a ranked plan of what to observe tonight, whats_up_tonight is usually better.\n",
        "inputSchema": {
          "properties": {
            "object_type": {
              "anyOf": [
                {
                  "enum": [
                    "asterism",
                    "dark_nebula",
                    "double_star",
                    "galaxy",
                    "globular_cluster",
                    "nebula",
                    "open_cluster",
                    "other",
                    "planetary_nebula",
                    "star",
                    "supernova_remnant"
                  ],
                  "type": "string"
                },
                {
                  "type": "null"
                }
              ],
              "default": null,
              "description": "Kind of object to return",
              "title": "Object Type"
            },
            "constellation": {
              "anyOf": [
                {
                  "type": "string"
                },
                {
                  "type": "null"
                }
              ],
              "default": null,
              "description": "IAU constellation name or abbreviation, e.g. 'Sagittarius' or 'Sgr'",
              "title": "Constellation"
            },
            "max_magnitude": {
              "anyOf": [
                {
                  "type": "number"
                },
                {
                  "type": "null"
                }
              ],
              "default": null,
              "description": "Only objects at this magnitude or brighter",
              "title": "Max Magnitude"
            },
            "min_size_arcmin": {
              "anyOf": [
                {
                  "minimum": 0,
                  "type": "number"
                },
                {
                  "type": "null"
                }
              ],
              "default": null,
              "description": "Minimum major-axis size in arcminutes",
              "title": "Min Size Arcmin"
            },
            "messier_only": {
              "default": false,
              "description": "Only Messier objects",
              "title": "Messier Only",
              "type": "boolean"
            },
            "name_contains": {
              "anyOf": [
                {
                  "type": "string"
                },
                {
                  "type": "null"
                }
              ],
              "default": null,
              "description": "Substring of a catalog or common name, e.g. 'Veil'",
              "title": "Name Contains"
            },
            "visible_tonight": {
              "default": false,
              "description": "Only objects that clear min_altitude during tonight's dark window (needs a location)",
              "title": "Visible Tonight",
              "type": "boolean"
            },
            "min_altitude": {
              "default": 25.0,
              "description": "Minimum useful altitude in degrees",
              "maximum": 80,
              "minimum": 0,
              "title": "Min Altitude",
              "type": "number"
            },
            "date": {
              "anyOf": [
                {
                  "type": "string"
                },
                {
                  "type": "null"
                }
              ],
              "default": null,
              "description": "Local date (YYYY-MM-DD) whose evening starts the night. Omit for tonight.",
              "title": "Date"
            },
            "latitude": {
              "anyOf": [
                {
                  "maximum": 90,
                  "minimum": -90,
                  "type": "number"
                },
                {
                  "type": "null"
                }
              ],
              "default": null,
              "description": "Observer latitude in degrees (north positive). Omit to use place or the saved default.",
              "title": "Latitude"
            },
            "longitude": {
              "anyOf": [
                {
                  "maximum": 180,
                  "minimum": -180,
                  "type": "number"
                },
                {
                  "type": "null"
                }
              ],
              "default": null,
              "description": "Observer longitude in degrees (east positive). Omit to use place or the saved default.",
              "title": "Longitude"
            },
            "place": {
              "anyOf": [
                {
                  "type": "string"
                },
                {
                  "type": "null"
                }
              ],
              "default": null,
              "description": "Place name to observe from instead of coordinates, e.g. 'Moab, Utah'.",
              "title": "Place"
            },
            "limit": {
              "default": 25,
              "description": "Maximum results",
              "maximum": 200,
              "minimum": 1,
              "title": "Limit",
              "type": "integer"
            }
          },
          "type": "object",
          "title": "search_deep_skyArguments"
        },
        "name": "search_deep_sky",
        "outputSchema": {
          "type": "object",
          "additionalProperties": true,
          "title": "search_deep_skyDictOutput"
        }
      },
      {
        "annotations": {
          "idempotentHint": true,
          "openWorldHint": true,
          "readOnlyHint": true
        },
        "description": "Which IAU constellation an object or RA/Dec lies in, using the official boundaries.\n\nPlanets move between constellations, so use this rather than recalling where one is.\n",
        "inputSchema": {
          "properties": {
            "target": {
              "anyOf": [
                {
                  "type": "string"
                },
                {
                  "type": "null"
                }
              ],
              "default": null,
              "description": "Object name to locate; alternatively give ra_deg/dec_deg",
              "title": "Target"
            },
            "ra_deg": {
              "anyOf": [
                {
                  "exclusiveMaximum": 360,
                  "minimum": 0,
                  "type": "number"
                },
                {
                  "type": "null"
                }
              ],
              "default": null,
              "description": "Right ascension, decimal degrees (J2000)",
              "title": "Ra Deg"
            },
            "dec_deg": {
              "anyOf": [
                {
                  "maximum": 90,
                  "minimum": -90,
                  "type": "number"
                },
                {
                  "type": "null"
                }
              ],
              "default": null,
              "description": "Declination, decimal degrees (J2000)",
              "title": "Dec Deg"
            }
          },
          "type": "object",
          "title": "identify_constellationArguments"
        },
        "name": "identify_constellation",
        "outputSchema": {
          "type": "object",
          "additionalProperties": true,
          "title": "identify_constellationDictOutput"
        }
      },
      {
        "annotations": {
          "idempotentHint": true,
          "openWorldHint": true,
          "readOnlyHint": true
        },
        "description": "Where an object is in the sky at a given moment from a given place.\n\nReturns altitude, azimuth, compass direction, airmass, RA/Dec (J2000 and of date),\nconstellation and magnitude. Use for 'where is Jupiter right now', 'which way do I look for\nM31 at 10pm' and similar; positions depend on time and place and should be computed.\n",
        "inputSchema": {
          "properties": {
            "target": {
              "description": "Planet, 'Moon', catalog name (M42, NGC 7000, Caldwell 14), common name (Ring Nebula) or SIMBAD identifier",
              "title": "Target",
              "type": "string"
            },
            "time": {
              "anyOf": [
                {
                  "type": "string"
                },
                {
                  "type": "null"
                }
              ],
              "default": null,
              "description": "ISO 8601 time; without an offset it is the observer's local time. Omit for now.",
              "title": "Time"
            },
            "latitude": {
              "anyOf": [
                {
                  "maximum": 90,
                  "minimum": -90,
                  "type": "number"
                },
                {
                  "type": "null"
                }
              ],
              "default": null,
              "description": "Observer latitude in degrees (north positive). Omit to use place or the saved default.",
              "title": "Latitude"
            },
            "longitude": {
              "anyOf": [
                {
                  "maximum": 180,
                  "minimum": -180,
                  "type": "number"
                },
                {
                  "type": "null"
                }
              ],
              "default": null,
              "description": "Observer longitude in degrees (east positive). Omit to use place or the saved default.",
              "title": "Longitude"
            },
            "place": {
              "anyOf": [
                {
                  "type": "string"
                },
                {
                  "type": "null"
                }
              ],
              "default": null,
              "description": "Place name to observe from instead of coordinates, e.g. 'Moab, Utah'.",
              "title": "Place"
            }
          },
          "required": [
            "target"
          ],
          "type": "object",
          "title": "get_positionArguments"
        },
        "name": "get_position",
        "outputSchema": {
          "type": "object",
          "additionalProperties": true,
          "title": "get_positionDictOutput"
        }
      },
      {
        "annotations": {
          "idempotentHint": true,
          "openWorldHint": true,
          "readOnlyHint": true
        },
        "description": "When an object rises, reaches its highest point, and sets on a given date and place.\n\nWorks for the Moon, planets, stars and deep-sky objects, and reports circumpolar or\nnever-rises cases. For the Sun's times and twilight, use get_twilight_times.\n",
        "inputSchema": {
          "properties": {
            "target": {
              "description": "Planet, 'Moon', catalog name (M42, NGC 7000, Caldwell 14), common name (Ring Nebula) or SIMBAD identifier",
              "title": "Target",
              "type": "string"
            },
            "date": {
              "anyOf": [
                {
                  "type": "string"
                },
                {
                  "type": "null"
                }
              ],
              "default": null,
              "description": "Local date (YYYY-MM-DD) whose evening starts the night. Omit for tonight.",
              "title": "Date"
            },
            "latitude": {
              "anyOf": [
                {
                  "maximum": 90,
                  "minimum": -90,
                  "type": "number"
                },
                {
                  "type": "null"
                }
              ],
              "default": null,
              "description": "Observer latitude in degrees (north positive). Omit to use place or the saved default.",
              "title": "Latitude"
            },
            "longitude": {
              "anyOf": [
                {
                  "maximum": 180,
                  "minimum": -180,
                  "type": "number"
                },
                {
                  "type": "null"
                }
              ],
              "default": null,
              "description": "Observer longitude in degrees (east positive). Omit to use place or the saved default.",
              "title": "Longitude"
            },
            "place": {
              "anyOf": [
                {
                  "type": "string"
                },
                {
                  "type": "null"
                }
              ],
              "default": null,
              "description": "Place name to observe from instead of coordinates, e.g. 'Moab, Utah'.",
              "title": "Place"
            }
          },
          "required": [
            "target"
          ],
          "type": "object",
          "title": "get_rise_set_transitArguments"
        },
        "name": "get_rise_set_transit",
        "outputSchema": {
          "type": "object",
          "additionalProperties": true,
          "title": "get_rise_set_transitDictOutput"
        }
      },
      {
        "annotations": {
          "idempotentHint": true,
          "openWorldHint": true,
          "readOnlyHint": true
        },
        "description": "Sunset, twilight stages, sunrise, when it gets fully dark, and moonrise/moonset.\n\nUse for 'when does it get dark', 'when is astronomical twilight' or 'how many hours of\nmoonless darkness tonight'.\n",
        "inputSchema": {
          "properties": {
            "date": {
              "anyOf": [
                {
                  "type": "string"
                },
                {
                  "type": "null"
                }
              ],
              "default": null,
              "description": "Local date (YYYY-MM-DD) whose evening starts the night. Omit for tonight.",
              "title": "Date"
            },
            "latitude": {
              "anyOf": [
                {
                  "maximum": 90,
                  "minimum": -90,
                  "type": "number"
                },
                {
                  "type": "null"
                }
              ],
              "default": null,
              "description": "Observer latitude in degrees (north positive). Omit to use place or the saved default.",
              "title": "Latitude"
            },
            "longitude": {
              "anyOf": [
                {
                  "maximum": 180,
                  "minimum": -180,
                  "type": "number"
                },
                {
                  "type": "null"
                }
              ],
              "default": null,
              "description": "Observer longitude in degrees (east positive). Omit to use place or the saved default.",
              "title": "Longitude"
            },
            "place": {
              "anyOf": [
                {
                  "type": "string"
                },
                {
                  "type": "null"
                }
              ],
              "default": null,
              "description": "Place name to observe from instead of coordinates, e.g. 'Moab, Utah'.",
              "title": "Place"
            }
          },
          "type": "object",
          "title": "get_twilight_timesArguments"
        },
        "name": "get_twilight_times",
        "outputSchema": {
          "type": "object",
          "additionalProperties": true,
          "title": "get_twilight_timesDictOutput"
        }
      },
      {
        "annotations": {
          "idempotentHint": true,
          "openWorldHint": true,
          "readOnlyHint": true
        },
        "description": "Current Moon phase and illumination, plus exact times of upcoming new, first quarter,\nfull and last quarter Moons.\n\nUse for 'when is the next full/new Moon' or planning dark-sky nights. Times use the saved\ndefault location's timezone, else UTC.\n",
        "inputSchema": {
          "properties": {
            "start_date": {
              "anyOf": [
                {
                  "type": "string"
                },
                {
                  "type": "null"
                }
              ],
              "default": null,
              "description": "First day (YYYY-MM-DD); omit for today",
              "title": "Start Date"
            },
            "days": {
              "default": 45,
              "description": "How many days of primary phases to list",
              "maximum": 400,
              "minimum": 1,
              "title": "Days",
              "type": "integer"
            }
          },
          "type": "object",
          "title": "get_moon_phasesArguments"
        },
        "name": "get_moon_phases",
        "outputSchema": {
          "type": "object",
          "additionalProperties": true,
          "title": "get_moon_phasesDictOutput"
        }
      },
      {
        "annotations": {
          "idempotentHint": true,
          "openWorldHint": true,
          "readOnlyHint": true
        },
        "description": "Where the Sun, Moon and planets are now (or at a given time) and how they look.\n\nReturns magnitude, phase, apparent size, distance, constellation, morning/evening sky, and\nwith a location the altitude, direction and rise/transit/set times. Use for 'which planets\nare up', 'where is Mars' or 'is Venus a morning or evening star'.\n",
        "inputSchema": {
          "properties": {
            "time": {
              "anyOf": [
                {
                  "type": "string"
                },
                {
                  "type": "null"
                }
              ],
              "default": null,
              "description": "ISO 8601 time; without an offset it is the observer's local time. Omit for now.",
              "title": "Time"
            },
            "latitude": {
              "anyOf": [
                {
                  "maximum": 90,
                  "minimum": -90,
                  "type": "number"
                },
                {
                  "type": "null"
                }
              ],
              "default": null,
              "description": "Observer latitude in degrees (north positive). Omit to use place or the saved default.",
              "title": "Latitude"
            },
            "longitude": {
              "anyOf": [
                {
                  "maximum": 180,
                  "minimum": -180,
                  "type": "number"
                },
                {
                  "type": "null"
                }
              ],
              "default": null,
              "description": "Observer longitude in degrees (east positive). Omit to use place or the saved default.",
              "title": "Longitude"
            },
            "place": {
              "anyOf": [
                {
                  "type": "string"
                },
                {
                  "type": "null"
                }
              ],
              "default": null,
              "description": "Place name to observe from instead of coordinates, e.g. 'Moab, Utah'.",
              "title": "Place"
            }
          },
          "type": "object",
          "title": "get_planet_positionsArguments"
        },
        "name": "get_planet_positions",
        "outputSchema": {
          "type": "object",
          "additionalProperties": true,
          "title": "get_planet_positionsDictOutput"
        }
      },
      {
        "annotations": {
          "idempotentHint": true,
          "openWorldHint": true,
          "readOnlyHint": true
        },
        "description": "Ranked list of what is worth observing on a given night from a given place.\n\nUse for 'what can I see tonight', 'what should I point my telescope at' or 'what's up this\nweekend'. Considers darkness, the Moon, light pollution (atlas or user-supplied Bortle),\nterrain, and the equipment's reach. Each entry has difficulty, best time, altitude, direction\nand viewing window. Does not check clouds; pair with get_sky_forecast for that.\n",
        "inputSchema": {
          "properties": {
            "date": {
              "anyOf": [
                {
                  "type": "string"
                },
                {
                  "type": "null"
                }
              ],
              "default": null,
              "description": "Local date (YYYY-MM-DD) whose evening starts the night. Omit for tonight.",
              "title": "Date"
            },
            "equipment": {
              "default": "telescope",
              "description": "What the observer is using",
              "enum": [
                "naked_eye",
                "binoculars",
                "telescope"
              ],
              "title": "Equipment",
              "type": "string"
            },
            "aperture_mm": {
              "anyOf": [
                {
                  "exclusiveMinimum": 0,
                  "maximum": 2000,
                  "type": "number"
                },
                {
                  "type": "null"
                }
              ],
              "default": null,
              "description": "Aperture in mm (defaults: binoculars 50, telescope 150)",
              "title": "Aperture Mm"
            },
            "bortle": {
              "anyOf": [
                {
                  "maximum": 9,
                  "minimum": 1,
                  "type": "integer"
                },
                {
                  "type": "null"
                }
              ],
              "default": null,
              "description": "Bortle class of the sky (1 pristine to 9 inner city). Omit to use the saved value or the light-pollution atlas.",
              "title": "Bortle"
            },
            "include": {
              "default": "all",
              "description": "Which kinds of targets",
              "enum": [
                "all",
                "planets",
                "deep_sky"
              ],
              "title": "Include",
              "type": "string"
            },
            "object_types": {
              "anyOf": [
                {
                  "items": {
                    "enum": [
                      "asterism",
                      "dark_nebula",
                      "double_star",
                      "galaxy",
                      "globular_cluster",
                      "nebula",
                      "open_cluster",
                      "other",
                      "planetary_nebula",
                      "star",
                      "supernova_remnant"
                    ],
                    "type": "string"
                  },
                  "type": "array"
                },
                {
                  "type": "null"
                }
              ],
              "default": null,
              "description": "Restrict deep-sky results to these kinds",
              "title": "Object Types"
            },
            "min_altitude": {
              "default": 25.0,
              "description": "Minimum useful altitude in degrees",
              "maximum": 80,
              "minimum": 0,
              "title": "Min Altitude",
              "type": "number"
            },
            "max_results": {
              "default": 20,
              "description": "Maximum targets",
              "maximum": 100,
              "minimum": 1,
              "title": "Max Results",
              "type": "integer"
            },
            "terrain": {
              "default": true,
              "description": "Account for hills and mountains on the local horizon (first use per location takes a few seconds)",
              "title": "Terrain",
              "type": "boolean"
            },
            "latitude": {
              "anyOf": [
                {
                  "maximum": 90,
                  "minimum": -90,
                  "type": "number"
                },
                {
                  "type": "null"
                }
              ],
              "default": null,
              "description": "Observer latitude in degrees (north positive). Omit to use place or the saved default.",
              "title": "Latitude"
            },
            "longitude": {
              "anyOf": [
                {
                  "maximum": 180,
                  "minimum": -180,
                  "type": "number"
                },
                {
                  "type": "null"
                }
              ],
              "default": null,
              "description": "Observer longitude in degrees (east positive). Omit to use place or the saved default.",
              "title": "Longitude"
            },
            "place": {
              "anyOf": [
                {
                  "type": "string"
                },
                {
                  "type": "null"
                }
              ],
              "default": null,
              "description": "Place name to observe from instead of coordinates, e.g. 'Moab, Utah'.",
              "title": "Place"
            }
          },
          "type": "object",
          "title": "whats_up_tonightArguments"
        },
        "name": "whats_up_tonight",
        "outputSchema": {
          "type": "object",
          "additionalProperties": true,
          "title": "whats_up_tonightDictOutput"
        }
      },
      {
        "annotations": {
          "idempotentHint": true,
          "openWorldHint": true,
          "readOnlyHint": true
        },
        "description": "Whether one specific object can be seen on a given night, and when and where to look.\n\nUse for 'can I see Saturn tonight', 'is the Andromeda Galaxy visible from here' and similar,\neven when the question sounds casual. Returns yes/no with reasons (too low, behind terrain,\ntoo faint for the sky and equipment), difficulty, best time, direction and Moon interference.\nDoes not check clouds; use get_sky_forecast for that.\n",
        "inputSchema": {
          "properties": {
            "target": {
              "description": "Planet, 'Moon', catalog name (M42, NGC 7000, Caldwell 14), common name (Ring Nebula) or SIMBAD identifier",
              "title": "Target",
              "type": "string"
            },
            "date": {
              "anyOf": [
                {
                  "type": "string"
                },
                {
                  "type": "null"
                }
              ],
              "default": null,
              "description": "Local date (YYYY-MM-DD) whose evening starts the night. Omit for tonight.",
              "title": "Date"
            },
            "equipment": {
              "default": "telescope",
              "description": "What the observer is using",
              "enum": [
                "naked_eye",
                "binoculars",
                "telescope"
              ],
              "title": "Equipment",
              "type": "string"
            },
            "aperture_mm": {
              "anyOf": [
                {
                  "exclusiveMinimum": 0,
                  "maximum": 2000,
                  "type": "number"
                },
                {
                  "type": "null"
                }
              ],
              "default": null,
              "description": "Aperture in mm (defaults: binoculars 50, telescope 150)",
              "title": "Aperture Mm"
            },
            "bortle": {
              "anyOf": [
                {
                  "maximum": 9,
                  "minimum": 1,
                  "type": "integer"
                },
                {
                  "type": "null"
                }
              ],
              "default": null,
              "description": "Bortle class of the sky (1 pristine to 9 inner city). Omit to use the saved value or the light-pollution atlas.",
              "title": "Bortle"
            },
            "min_altitude": {
              "default": 20.0,
              "description": "Minimum useful altitude in degrees",
              "maximum": 80,
              "minimum": 0,
              "title": "Min Altitude",
              "type": "number"
            },
            "terrain": {
              "default": true,
              "description": "Account for hills and mountains on the local horizon (first use per location takes a few seconds)",
              "title": "Terrain",
              "type": "boolean"
            },
            "latitude": {
              "anyOf": [
                {
                  "maximum": 90,
                  "minimum": -90,
                  "type": "number"
                },
                {
                  "type": "null"
                }
              ],
              "default": null,
              "description": "Observer latitude in degrees (north positive). Omit to use place or the saved default.",
              "title": "Latitude"
            },
            "longitude": {
              "anyOf": [
                {
                  "maximum": 180,
                  "minimum": -180,
                  "type": "number"
                },
                {
                  "type": "null"
                }
              ],
              "default": null,
              "description": "Observer longitude in degrees (east positive). Omit to use place or the saved default.",
              "title": "Longitude"
            },
            "place": {
              "anyOf": [
                {
                  "type": "string"
                },
                {
                  "type": "null"
                }
              ],
              "default": null,
              "description": "Place name to observe from instead of coordinates, e.g. 'Moab, Utah'.",
              "title": "Place"
            }
          },
          "required": [
            "target"
          ],
          "type": "object",
          "title": "is_visible_tonightArguments"
        },
        "name": "is_visible_tonight",
        "outputSchema": {
          "type": "object",
          "additionalProperties": true,
          "title": "is_visible_tonightDictOutput"
        }
      },
      {
        "annotations": {
          "idempotentHint": true,
          "openWorldHint": true,
          "readOnlyHint": true
        },
        "description": "Compare upcoming nights and pick the best ones, for one target or for dark-sky observing.\n\nUse for 'which night this week is best for the Orion Nebula', 'when should I go out this\nmonth' or 'best night for Saturn'. Scores each night on how long the target is well placed\nin darkness, how high it gets, how much moonlight brightens the sky near it, and the cloud\nforecast. Clouds are only forecast about 16 days ahead, so later nights are ranked separately\non Moon and altitude alone. For one night's detail, follow up with is_visible_tonight and\nget_sky_forecast.\n",
        "inputSchema": {
          "properties": {
            "target": {
              "anyOf": [
                {
                  "type": "string"
                },
                {
                  "type": "null"
                }
              ],
              "default": null,
              "description": "Object to plan for: planet, 'Moon', catalog or common name. Omit to rate nights for general dark-sky observing.",
              "title": "Target"
            },
            "start_date": {
              "anyOf": [
                {
                  "type": "string"
                },
                {
                  "type": "null"
                }
              ],
              "default": null,
              "description": "First night to consider (YYYY-MM-DD); omit for tonight",
              "title": "Start Date"
            },
            "days": {
              "default": 30,
              "description": "How many nights to compare",
              "maximum": 60,
              "minimum": 2,
              "title": "Days",
              "type": "integer"
            },
            "min_altitude": {
              "default": 25.0,
              "description": "Minimum useful altitude in degrees",
              "maximum": 80,
              "minimum": 0,
              "title": "Min Altitude",
              "type": "number"
            },
            "bortle": {
              "anyOf": [
                {
                  "maximum": 9,
                  "minimum": 1,
                  "type": "integer"
                },
                {
                  "type": "null"
                }
              ],
              "default": null,
              "description": "Bortle class of the sky (1 pristine to 9 inner city). Omit to use the saved value or the light-pollution atlas.",
              "title": "Bortle"
            },
            "latitude": {
              "anyOf": [
                {
                  "maximum": 90,
                  "minimum": -90,
                  "type": "number"
                },
                {
                  "type": "null"
                }
              ],
              "default": null,
              "description": "Observer latitude in degrees (north positive). Omit to use place or the saved default.",
              "title": "Latitude"
            },
            "longitude": {
              "anyOf": [
                {
                  "maximum": 180,
                  "minimum": -180,
                  "type": "number"
                },
                {
                  "type": "null"
                }
              ],
              "default": null,
              "description": "Observer longitude in degrees (east positive). Omit to use place or the saved default.",
              "title": "Longitude"
            },
            "place": {
              "anyOf": [
                {
                  "type": "string"
                },
                {
                  "type": "null"
                }
              ],
              "default": null,
              "description": "Place name to observe from instead of coordinates, e.g. 'Moab, Utah'.",
              "title": "Place"
            }
          },
          "type": "object",
          "title": "best_night_this_monthArguments"
        },
        "name": "best_night_this_month",
        "outputSchema": {
          "type": "object",
          "additionalProperties": true,
          "title": "best_night_this_monthDictOutput"
        }
      },
      {
        "annotations": {
          "idempotentHint": true,
          "openWorldHint": true,
          "readOnlyHint": true
        },
        "description": "Upcoming weekends (Friday and Saturday nights) with little or no moonlight.\n\nUse for 'when is the next new-moon weekend', 'which weekends this summer are good for a\ndark-sky trip' or booking a campsite months ahead. With a location, counts the dark hours\neach night with the Moon down; without one, falls back to the Moon's illumination. Computed\noffline; weather is not considered.\n",
        "inputSchema": {
          "properties": {
            "start_date": {
              "anyOf": [
                {
                  "type": "string"
                },
                {
                  "type": "null"
                }
              ],
              "default": null,
              "description": "First day to consider (YYYY-MM-DD); omit for today",
              "title": "Start Date"
            },
            "months": {
              "default": 6,
              "description": "How many months ahead to search",
              "maximum": 24,
              "minimum": 1,
              "title": "Months",
              "type": "integer"
            },
            "min_moon_free_pct": {
              "default": 70.0,
              "description": "Minimum share of the two nights' dark hours with the Moon below the horizon",
              "maximum": 100,
              "minimum": 30,
              "title": "Min Moon Free Pct",
              "type": "number"
            },
            "latitude": {
              "anyOf": [
                {
                  "maximum": 90,
                  "minimum": -90,
                  "type": "number"
                },
                {
                  "type": "null"
                }
              ],
              "default": null,
              "description": "Observer latitude in degrees (north positive). Omit to use place or the saved default.",
              "title": "Latitude"
            },
            "longitude": {
              "anyOf": [
                {
                  "maximum": 180,
                  "minimum": -180,
                  "type": "number"
                },
                {
                  "type": "null"
                }
              ],
              "default": null,
              "description": "Observer longitude in degrees (east positive). Omit to use place or the saved default.",
              "title": "Longitude"
            },
            "place": {
              "anyOf": [
                {
                  "type": "string"
                },
                {
                  "type": "null"
                }
              ],
              "default": null,
              "description": "Place name to observe from instead of coordinates, e.g. 'Moab, Utah'.",
              "title": "Place"
            }
          },
          "type": "object",
          "title": "find_dark_moon_weekendsArguments"
        },
        "name": "find_dark_moon_weekends",
        "outputSchema": {
          "type": "object",
          "additionalProperties": true,
          "title": "find_dark_moon_weekendsDictOutput"
        }
      },
      {
        "annotations": {
          "idempotentHint": true,
          "openWorldHint": true,
          "readOnlyHint": true
        },
        "description": "Night-time observing weather: will it be clear, and when.\n\nHour-by-hour from sunset to sunrise: cloud cover by layer, humidity, dew point, wind and\nprecipitation chance, plus seeing and transparency about 3 days out. Summarises a 0-100\nscore, clear hours, the longest clear stretch and dew risk. Up to ~16 days ahead.\n",
        "inputSchema": {
          "properties": {
            "date": {
              "anyOf": [
                {
                  "type": "string"
                },
                {
                  "type": "null"
                }
              ],
              "default": null,
              "description": "Local date (YYYY-MM-DD) whose evening starts the night. Omit for tonight.",
              "title": "Date"
            },
            "units": {
              "default": "metric",
              "description": "Units for temperature and wind",
              "enum": [
                "metric",
                "imperial"
              ],
              "title": "Units",
              "type": "string"
            },
            "latitude": {
              "anyOf": [
                {
                  "maximum": 90,
                  "minimum": -90,
                  "type": "number"
                },
                {
                  "type": "null"
                }
              ],
              "default": null,
              "description": "Observer latitude in degrees (north positive). Omit to use place or the saved default.",
              "title": "Latitude"
            },
            "longitude": {
              "anyOf": [
                {
                  "maximum": 180,
                  "minimum": -180,
                  "type": "number"
                },
                {
                  "type": "null"
                }
              ],
              "default": null,
              "description": "Observer longitude in degrees (east positive). Omit to use place or the saved default.",
              "title": "Longitude"
            },
            "place": {
              "anyOf": [
                {
                  "type": "string"
                },
                {
                  "type": "null"
                }
              ],
              "default": null,
              "description": "Place name to observe from instead of coordinates, e.g. 'Moab, Utah'.",
              "title": "Place"
            }
          },
          "type": "object",
          "title": "get_sky_forecastArguments"
        },
        "name": "get_sky_forecast",
        "outputSchema": {
          "type": "object",
          "additionalProperties": true,
          "title": "get_sky_forecastDictOutput"
        }
      },
      {
        "annotations": {
          "idempotentHint": true,
          "openWorldHint": true,
          "readOnlyHint": true
        },
        "description": "What is dimming a night's sky besides clouds: wildfire smoke, dust and other aerosols.\n\nUse for 'is it smoky tonight', 'why is the sky so hazy' or 'will the Milky Way look washed\nout'. Hour-by-hour aerosol optical depth, dust and fine particles from sunset to sunrise,\nwith a transparency rating, the likely cause and the extra extinction in magnitudes. About\n5 days ahead. Clouds, humidity and seeing are in get_sky_forecast.\n",
        "inputSchema": {
          "properties": {
            "date": {
              "anyOf": [
                {
                  "type": "string"
                },
                {
                  "type": "null"
                }
              ],
              "default": null,
              "description": "Local date (YYYY-MM-DD) whose evening starts the night. Omit for tonight.",
              "title": "Date"
            },
            "latitude": {
              "anyOf": [
                {
                  "maximum": 90,
                  "minimum": -90,
                  "type": "number"
                },
                {
                  "type": "null"
                }
              ],
              "default": null,
              "description": "Observer latitude in degrees (north positive). Omit to use place or the saved default.",
              "title": "Latitude"
            },
            "longitude": {
              "anyOf": [
                {
                  "maximum": 180,
                  "minimum": -180,
                  "type": "number"
                },
                {
                  "type": "null"
                }
              ],
              "default": null,
              "description": "Observer longitude in degrees (east positive). Omit to use place or the saved default.",
              "title": "Longitude"
            },
            "place": {
              "anyOf": [
                {
                  "type": "string"
                },
                {
                  "type": "null"
                }
              ],
              "default": null,
              "description": "Place name to observe from instead of coordinates, e.g. 'Moab, Utah'.",
              "title": "Place"
            }
          },
          "type": "object",
          "title": "get_transparency_driversArguments"
        },
        "name": "get_transparency_drivers",
        "outputSchema": {
          "type": "object",
          "additionalProperties": true,
          "title": "get_transparency_driversDictOutput"
        }
      },
      {
        "annotations": {
          "idempotentHint": true,
          "openWorldHint": true,
          "readOnlyHint": true
        },
        "description": "Estimate the faintest stars visible for a sky and piece of equipment, including moonlight.\n\nUse for 'how faint can my telescope go' or 'how many stars will I see'. Sky darkness comes\nfrom the user's Bortle/SQM or the light-pollution atlas. A model estimate.\n",
        "inputSchema": {
          "properties": {
            "equipment": {
              "default": "naked_eye",
              "description": "What the observer is using",
              "enum": [
                "naked_eye",
                "binoculars",
                "telescope"
              ],
              "title": "Equipment",
              "type": "string"
            },
            "aperture_mm": {
              "anyOf": [
                {
                  "exclusiveMinimum": 0,
                  "maximum": 2000,
                  "type": "number"
                },
                {
                  "type": "null"
                }
              ],
              "default": null,
              "description": "Aperture in mm (defaults: binoculars 50, telescope 150)",
              "title": "Aperture Mm"
            },
            "bortle": {
              "anyOf": [
                {
                  "maximum": 9,
                  "minimum": 1,
                  "type": "integer"
                },
                {
                  "type": "null"
                }
              ],
              "default": null,
              "description": "Bortle class of the sky (1 pristine to 9 inner city). Omit to use the saved value or the light-pollution atlas.",
              "title": "Bortle"
            },
            "sqm": {
              "anyOf": [
                {
                  "maximum": 22.5,
                  "minimum": 15,
                  "type": "number"
                },
                {
                  "type": "null"
                }
              ],
              "default": null,
              "description": "Measured sky brightness in mag/arcsec^2 (Sky Quality Meter)",
              "title": "Sqm"
            },
            "time": {
              "anyOf": [
                {
                  "type": "string"
                },
                {
                  "type": "null"
                }
              ],
              "default": null,
              "description": "ISO 8601 time; without an offset it is the observer's local time. Omit for now.",
              "title": "Time"
            },
            "include_moon": {
              "default": true,
              "description": "Account for moonlight at the given time (or tonight's mid-darkness)",
              "title": "Include Moon",
              "type": "boolean"
            },
            "latitude": {
              "anyOf": [
                {
                  "maximum": 90,
                  "minimum": -90,
                  "type": "number"
                },
                {
                  "type": "null"
                }
              ],
              "default": null,
              "description": "Observer latitude in degrees (north positive). Omit to use place or the saved default.",
              "title": "Latitude"
            },
            "longitude": {
              "anyOf": [
                {
                  "maximum": 180,
                  "minimum": -180,
                  "type": "number"
                },
                {
                  "type": "null"
                }
              ],
              "default": null,
              "description": "Observer longitude in degrees (east positive). Omit to use place or the saved default.",
              "title": "Longitude"
            },
            "place": {
              "anyOf": [
                {
                  "type": "string"
                },
                {
                  "type": "null"
                }
              ],
              "default": null,
              "description": "Place name to observe from instead of coordinates, e.g. 'Moab, Utah'.",
              "title": "Place"
            }
          },
          "type": "object",
          "title": "get_limiting_magnitudeArguments"
        },
        "name": "get_limiting_magnitude",
        "outputSchema": {
          "type": "object",
          "additionalProperties": true,
          "title": "get_limiting_magnitudeDictOutput"
        }
      },
      {
        "annotations": {
          "idempotentHint": true,
          "openWorldHint": true,
          "readOnlyHint": true
        },
        "description": "How light-polluted a location's sky is: atlas zone, sky brightness (mag/arcsec²), an\nestimated Bortle class, and the naked-eye limiting magnitude.\n\nUse for 'how dark is the sky at X', 'what Bortle class am I' or comparing sites. From the\n2025 Light Pollution Atlas (VIIRS satellite data); a modelled zenith value for a clear,\nmoonless night, not a measurement.\n",
        "inputSchema": {
          "properties": {
            "latitude": {
              "anyOf": [
                {
                  "maximum": 90,
                  "minimum": -90,
                  "type": "number"
                },
                {
                  "type": "null"
                }
              ],
              "default": null,
              "description": "Observer latitude in degrees (north positive). Omit to use place or the saved default.",
              "title": "Latitude"
            },
            "longitude": {
              "anyOf": [
                {
                  "maximum": 180,
                  "minimum": -180,
                  "type": "number"
                },
                {
                  "type": "null"
                }
              ],
              "default": null,
              "description": "Observer longitude in degrees (east positive). Omit to use place or the saved default.",
              "title": "Longitude"
            },
            "place": {
              "anyOf": [
                {
                  "type": "string"
                },
                {
                  "type": "null"
                }
              ],
              "default": null,
              "description": "Place name to observe from instead of coordinates, e.g. 'Moab, Utah'.",
              "title": "Place"
            }
          },
          "type": "object",
          "title": "get_light_pollutionArguments"
        },
        "name": "get_light_pollution",
        "outputSchema": {
          "type": "object",
          "additionalProperties": true,
          "title": "get_light_pollutionDictOutput"
        }
      },
      {
        "annotations": {
          "idempotentHint": true,
          "openWorldHint": true,
          "readOnlyHint": true
        },
        "description": "Suggest darker observing spots within a radius, each with nearby access points.\n\nUse for 'where can I go to see the Milky Way', 'darkest place within an hour of me' and\nsimilar. Ranks by the light-pollution atlas (darkest first, then closest), and keeps only\nspots with a mapped campground, viewpoint, picnic area, trailhead or named parking nearby\n(OpenStreetMap). Distances are straight-line; the user should check roads and access.\n",
        "inputSchema": {
          "properties": {
            "radius_km": {
              "default": 100,
              "description": "How far to search (straight-line km)",
              "maximum": 300,
              "minimum": 10,
              "title": "Radius Km",
              "type": "number"
            },
            "max_results": {
              "default": 5,
              "description": "How many sites to suggest",
              "maximum": 10,
              "minimum": 1,
              "title": "Max Results",
              "type": "integer"
            },
            "min_separation_km": {
              "default": 15,
              "description": "Minimum spacing between suggestions",
              "maximum": 100,
              "minimum": 2,
              "title": "Min Separation Km",
              "type": "number"
            },
            "latitude": {
              "anyOf": [
                {
                  "maximum": 90,
                  "minimum": -90,
                  "type": "number"
                },
                {
                  "type": "null"
                }
              ],
              "default": null,
              "description": "Observer latitude in degrees (north positive). Omit to use place or the saved default.",
              "title": "Latitude"
            },
            "longitude": {
              "anyOf": [
                {
                  "maximum": 180,
                  "minimum": -180,
                  "type": "number"
                },
                {
                  "type": "null"
                }
              ],
              "default": null,
              "description": "Observer longitude in degrees (east positive). Omit to use place or the saved default.",
              "title": "Longitude"
            },
            "place": {
              "anyOf": [
                {
                  "type": "string"
                },
                {
                  "type": "null"
                }
              ],
              "default": null,
              "description": "Place name to observe from instead of coordinates, e.g. 'Moab, Utah'.",
              "title": "Place"
            }
          },
          "type": "object",
          "title": "find_dark_sitesArguments"
        },
        "name": "find_dark_sites",
        "outputSchema": {
          "type": "object",
          "additionalProperties": true,
          "title": "find_dark_sitesDictOutput"
        }
      },
      {
        "annotations": {
          "idempotentHint": true,
          "openWorldHint": true,
          "readOnlyHint": true
        },
        "description": "How high the surrounding terrain rises in each direction from an observing site.\n\nUse for 'will the mountains block my view to the south' or before planning low targets.\nComputed from a 90 m elevation model out to 35 km with Earth curvature and refraction;\ntrees and buildings are not included. whats_up_tonight and is_visible_tonight already\napply this automatically.\n",
        "inputSchema": {
          "properties": {
            "latitude": {
              "anyOf": [
                {
                  "maximum": 90,
                  "minimum": -90,
                  "type": "number"
                },
                {
                  "type": "null"
                }
              ],
              "default": null,
              "description": "Observer latitude in degrees (north positive). Omit to use place or the saved default.",
              "title": "Latitude"
            },
            "longitude": {
              "anyOf": [
                {
                  "maximum": 180,
                  "minimum": -180,
                  "type": "number"
                },
                {
                  "type": "null"
                }
              ],
              "default": null,
              "description": "Observer longitude in degrees (east positive). Omit to use place or the saved default.",
              "title": "Longitude"
            },
            "place": {
              "anyOf": [
                {
                  "type": "string"
                },
                {
                  "type": "null"
                }
              ],
              "default": null,
              "description": "Place name to observe from instead of coordinates, e.g. 'Moab, Utah'.",
              "title": "Place"
            }
          },
          "type": "object",
          "title": "get_horizon_profileArguments"
        },
        "name": "get_horizon_profile",
        "outputSchema": {
          "type": "object",
          "additionalProperties": true,
          "title": "get_horizon_profileDictOutput"
        }
      },
      {
        "annotations": {
          "idempotentHint": true,
          "openWorldHint": true,
          "readOnlyHint": true
        },
        "description": "Upcoming lunar eclipses, and solar eclipses visible from the observer's location.\n\nIncludes whether the Moon is up at mid-eclipse, local contact times and how much of the\nSun is covered. Use rather than recalling eclipse dates.\n",
        "inputSchema": {
          "properties": {
            "years": {
              "default": 10,
              "description": "How many years ahead to search for local solar eclipses",
              "exclusiveMinimum": 0,
              "maximum": 30,
              "title": "Years",
              "type": "number"
            },
            "lunar_count": {
              "default": 6,
              "description": "How many upcoming lunar eclipses to list",
              "maximum": 30,
              "minimum": 1,
              "title": "Lunar Count",
              "type": "integer"
            },
            "latitude": {
              "anyOf": [
                {
                  "maximum": 90,
                  "minimum": -90,
                  "type": "number"
                },
                {
                  "type": "null"
                }
              ],
              "default": null,
              "description": "Observer latitude in degrees (north positive). Omit to use place or the saved default.",
              "title": "Latitude"
            },
            "longitude": {
              "anyOf": [
                {
                  "maximum": 180,
                  "minimum": -180,
                  "type": "number"
                },
                {
                  "type": "null"
                }
              ],
              "default": null,
              "description": "Observer longitude in degrees (east positive). Omit to use place or the saved default.",
              "title": "Longitude"
            },
            "place": {
              "anyOf": [
                {
                  "type": "string"
                },
                {
                  "type": "null"
                }
              ],
              "default": null,
              "description": "Place name to observe from instead of coordinates, e.g. 'Moab, Utah'.",
              "title": "Place"
            }
          },
          "type": "object",
          "title": "get_eclipsesArguments"
        },
        "name": "get_eclipses",
        "outputSchema": {
          "type": "object",
          "additionalProperties": true,
          "title": "get_eclipsesDictOutput"
        }
      },
      {
        "annotations": {
          "idempotentHint": true,
          "openWorldHint": true,
          "readOnlyHint": true
        },
        "description": "Upcoming close pairings of planets in the sky (optionally with the Moon and bright stars).\n\nUse for 'when are Venus and Jupiter close together', 'any conjunctions this year', 'when\nis the Moon next to Saturn' or 'when does Mars pass Regulus'. Returns the moment of\nclosest approach, the separation, which body is to the north, the constellation, and\nwhether it is a morning or evening event. Computed offline for the centre of the Earth; a\nlocation only adds local times and whether the pair is up at that moment.\n",
        "inputSchema": {
          "properties": {
            "start_date": {
              "anyOf": [
                {
                  "type": "string"
                },
                {
                  "type": "null"
                }
              ],
              "default": null,
              "description": "First day (YYYY-MM-DD); omit for today",
              "title": "Start Date"
            },
            "days": {
              "default": 365,
              "description": "How many days ahead to search",
              "maximum": 1830,
              "minimum": 1,
              "title": "Days",
              "type": "integer"
            },
            "max_separation_deg": {
              "default": 5.0,
              "description": "Only pairings at least this close",
              "exclusiveMinimum": 0,
              "maximum": 15,
              "title": "Max Separation Deg",
              "type": "number"
            },
            "include_moon": {
              "default": false,
              "description": "Also list the Moon passing each planet (about one per planet per month; best with a short range)",
              "title": "Include Moon",
              "type": "boolean"
            },
            "body": {
              "anyOf": [
                {
                  "enum": [
                    "moon",
                    "mercury",
                    "venus",
                    "mars",
                    "jupiter",
                    "saturn",
                    "uranus",
                    "neptune"
                  ],
                  "type": "string"
                },
                {
                  "type": "null"
                }
              ],
              "default": null,
              "description": "Only pairings that involve this body",
              "title": "Body"
            },
            "min_elongation_deg": {
              "default": 12.0,
              "description": "Skip pairings closer to the Sun than this; 0 keeps everything",
              "maximum": 60,
              "minimum": 0,
              "title": "Min Elongation Deg",
              "type": "number"
            },
            "include_stars": {
              "default": false,
              "description": "Also pair the planets (and the Moon, if included) with bright stars and clusters near the ecliptic: Regulus, Spica, Antares, Aldebaran, Pollux, the Pleiades, the Beehive and a few more",
              "title": "Include Stars",
              "type": "boolean"
            },
            "latitude": {
              "anyOf": [
                {
                  "maximum": 90,
                  "minimum": -90,
                  "type": "number"
                },
                {
                  "type": "null"
                }
              ],
              "default": null,
              "description": "Observer latitude in degrees (north positive). Omit to use place or the saved default.",
              "title": "Latitude"
            },
            "longitude": {
              "anyOf": [
                {
                  "maximum": 180,
                  "minimum": -180,
                  "type": "number"
                },
                {
                  "type": "null"
                }
              ],
              "default": null,
              "description": "Observer longitude in degrees (east positive). Omit to use place or the saved default.",
              "title": "Longitude"
            },
            "place": {
              "anyOf": [
                {
                  "type": "string"
                },
                {
                  "type": "null"
                }
              ],
              "default": null,
              "description": "Place name to observe from instead of coordinates, e.g. 'Moab, Utah'.",
              "title": "Place"
            }
          },
          "type": "object",
          "title": "find_conjunctionsArguments"
        },
        "name": "find_conjunctions",
        "outputSchema": {
          "type": "object",
          "additionalProperties": true,
          "title": "find_conjunctionsDictOutput"
        }
      },
      {
        "annotations": {
          "idempotentHint": true,
          "openWorldHint": true,
          "readOnlyHint": true
        },
        "description": "When Mercury and Venus are farthest from the Sun in the sky: their best evening and morning showings.\n\nUse for 'when can I see Mercury', 'when is Venus highest in the evening' or 'best Mercury\napparition this year'. Gives the date, elongation, morning or evening sky, magnitude and\nphase, and with a location how high the planet stands at civil twilight, which is what\nmakes an apparition easy or hard. Computed offline.\n",
        "inputSchema": {
          "properties": {
            "start_date": {
              "anyOf": [
                {
                  "type": "string"
                },
                {
                  "type": "null"
                }
              ],
              "default": null,
              "description": "First day (YYYY-MM-DD); omit for today",
              "title": "Start Date"
            },
            "days": {
              "default": 365,
              "description": "How many days ahead to search",
              "maximum": 3650,
              "minimum": 1,
              "title": "Days",
              "type": "integer"
            },
            "planets": {
              "anyOf": [
                {
                  "items": {
                    "enum": [
                      "mercury",
                      "venus"
                    ],
                    "type": "string"
                  },
                  "type": "array"
                },
                {
                  "type": "null"
                }
              ],
              "default": null,
              "description": "Mercury, Venus or both (default)",
              "title": "Planets"
            },
            "latitude": {
              "anyOf": [
                {
                  "maximum": 90,
                  "minimum": -90,
                  "type": "number"
                },
                {
                  "type": "null"
                }
              ],
              "default": null,
              "description": "Observer latitude in degrees (north positive). Omit to use place or the saved default.",
              "title": "Latitude"
            },
            "longitude": {
              "anyOf": [
                {
                  "maximum": 180,
                  "minimum": -180,
                  "type": "number"
                },
                {
                  "type": "null"
                }
              ],
              "default": null,
              "description": "Observer longitude in degrees (east positive). Omit to use place or the saved default.",
              "title": "Longitude"
            },
            "place": {
              "anyOf": [
                {
                  "type": "string"
                },
                {
                  "type": "null"
                }
              ],
              "default": null,
              "description": "Place name to observe from instead of coordinates, e.g. 'Moab, Utah'.",
              "title": "Place"
            }
          },
          "type": "object",
          "title": "find_greatest_elongationsArguments"
        },
        "name": "find_greatest_elongations",
        "outputSchema": {
          "type": "object",
          "additionalProperties": true,
          "title": "find_greatest_elongationsDictOutput"
        }
      },
      {
        "annotations": {
          "idempotentHint": true,
          "openWorldHint": true,
          "readOnlyHint": true
        },
        "description": "Upcoming oppositions of Mars, Jupiter, Saturn, Uranus and Neptune: when each planet is\nopposite the Sun, up all night, and at its biggest and brightest.\n\nUse for 'when is the next Mars opposition', 'when is Saturn best this year' or 'how close\ndoes Mars get in 2027'. Gives the date, constellation, magnitude, apparent size, distance,\nthe date of closest approach to Earth, and with a location how high the planet climbs.\nComputed offline; use rather than recalling dates.\n",
        "inputSchema": {
          "properties": {
            "start_date": {
              "anyOf": [
                {
                  "type": "string"
                },
                {
                  "type": "null"
                }
              ],
              "default": null,
              "description": "First day (YYYY-MM-DD); omit for today",
              "title": "Start Date"
            },
            "years": {
              "default": 3,
              "description": "How many years ahead to search (Mars comes to opposition only every 26 months)",
              "exclusiveMinimum": 0,
              "maximum": 30,
              "title": "Years",
              "type": "number"
            },
            "planets": {
              "anyOf": [
                {
                  "items": {
                    "enum": [
                      "mars",
                      "jupiter",
                      "saturn",
                      "uranus",
                      "neptune"
                    ],
                    "type": "string"
                  },
                  "type": "array"
                },
                {
                  "type": "null"
                }
              ],
              "default": null,
              "description": "Restrict to these planets; omit for Mars through Neptune",
              "title": "Planets"
            },
            "latitude": {
              "anyOf": [
                {
                  "maximum": 90,
                  "minimum": -90,
                  "type": "number"
                },
                {
                  "type": "null"
                }
              ],
              "default": null,
              "description": "Observer latitude in degrees (north positive). Omit to use place or the saved default.",
              "title": "Latitude"
            },
            "longitude": {
              "anyOf": [
                {
                  "maximum": 180,
                  "minimum": -180,
                  "type": "number"
                },
                {
                  "type": "null"
                }
              ],
              "default": null,
              "description": "Observer longitude in degrees (east positive). Omit to use place or the saved default.",
              "title": "Longitude"
            },
            "place": {
              "anyOf": [
                {
                  "type": "string"
                },
                {
                  "type": "null"
                }
              ],
              "default": null,
              "description": "Place name to observe from instead of coordinates, e.g. 'Moab, Utah'.",
              "title": "Place"
            }
          },
          "type": "object",
          "title": "find_oppositionsArguments"
        },
        "name": "find_oppositions",
        "outputSchema": {
          "type": "object",
          "additionalProperties": true,
          "title": "find_oppositionsDictOutput"
        }
      },
      {
        "annotations": {
          "idempotentHint": true,
          "openWorldHint": true,
          "readOnlyHint": true
        },
        "description": "Where Io, Europa, Ganymede and Callisto are relative to Jupiter at a given moment.\n\nUse for 'which moon is which', 'why can I only see three moons' or 'is the Red Spot facing\nus right now'. Gives each moon's side and distance from the planet, whether it is in\ntransit, hidden behind Jupiter or in its shadow, any moon shadow on the disk, the\neast-to-west line-up, the central meridian longitudes and where the Great Red Spot is.\nComputed offline. For upcoming transits and eclipses, use get_jupiter_events.\n",
        "inputSchema": {
          "properties": {
            "time": {
              "anyOf": [
                {
                  "type": "string"
                },
                {
                  "type": "null"
                }
              ],
              "default": null,
              "description": "ISO 8601 time; without an offset it is the observer's local time. Omit for now.",
              "title": "Time"
            },
            "grs_longitude": {
              "anyOf": [
                {
                  "exclusiveMaximum": 360,
                  "minimum": 0,
                  "type": "number"
                },
                {
                  "type": "null"
                }
              ],
              "default": null,
              "description": "Great Red Spot's System II longitude, if you have a current measurement; omit to use the latest JUPOS value and its drift",
              "title": "Grs Longitude"
            },
            "latitude": {
              "anyOf": [
                {
                  "maximum": 90,
                  "minimum": -90,
                  "type": "number"
                },
                {
                  "type": "null"
                }
              ],
              "default": null,
              "description": "Observer latitude in degrees (north positive). Omit to use place or the saved default.",
              "title": "Latitude"
            },
            "longitude": {
              "anyOf": [
                {
                  "maximum": 180,
                  "minimum": -180,
                  "type": "number"
                },
                {
                  "type": "null"
                }
              ],
              "default": null,
              "description": "Observer longitude in degrees (east positive). Omit to use place or the saved default.",
              "title": "Longitude"
            },
            "place": {
              "anyOf": [
                {
                  "type": "string"
                },
                {
                  "type": "null"
                }
              ],
              "default": null,
              "description": "Place name to observe from instead of coordinates, e.g. 'Moab, Utah'.",
              "title": "Place"
            }
          },
          "type": "object",
          "title": "get_jupiter_moonsArguments"
        },
        "name": "get_jupiter_moons",
        "outputSchema": {
          "type": "object",
          "additionalProperties": true,
          "title": "get_jupiter_moonsDictOutput"
        }
      },
      {
        "annotations": {
          "idempotentHint": true,
          "openWorldHint": true,
          "readOnlyHint": true
        },
        "description": "Upcoming events of Jupiter's moons and Great Red Spot, in time order.\n\nUse for 'when is the next shadow transit', 'when can I see the Great Red Spot tonight' or\n'any Io transits this week' or 'mutual events tonight'. Lists moon transits, shadow\ntransits, occultations and eclipses (start and end), Red Spot transits, and in season the\nmoons occulting and eclipsing each other, good to a few minutes. With a location, each\nevent says whether Jupiter is up in a dark sky. Computed offline; the Red Spot's longitude\ncomes from the latest JUPOS measurement available.\n",
        "inputSchema": {
          "properties": {
            "time": {
              "anyOf": [
                {
                  "type": "string"
                },
                {
                  "type": "null"
                }
              ],
              "default": null,
              "description": "Start of the search, ISO 8601; without an offset it is the observer's local time. Omit for now.",
              "title": "Time"
            },
            "hours": {
              "default": 24,
              "description": "How many hours ahead to search",
              "exclusiveMinimum": 0,
              "maximum": 240,
              "title": "Hours",
              "type": "number"
            },
            "observable_only": {
              "default": false,
              "description": "Keep only events with Jupiter at least 10° up in a dark sky at the location",
              "title": "Observable Only",
              "type": "boolean"
            },
            "include_mutual_events": {
              "default": true,
              "description": "Include moons occulting and eclipsing each other (only in seasons around Jupiter's equinoxes, such as late 2026 to mid 2027)",
              "title": "Include Mutual Events",
              "type": "boolean"
            },
            "grs_longitude": {
              "anyOf": [
                {
                  "exclusiveMaximum": 360,
                  "minimum": 0,
                  "type": "number"
                },
                {
                  "type": "null"
                }
              ],
              "default": null,
              "description": "Great Red Spot's System II longitude, if you have a current measurement; omit to use the latest JUPOS value and its drift",
              "title": "Grs Longitude"
            },
            "latitude": {
              "anyOf": [
                {
                  "maximum": 90,
                  "minimum": -90,
                  "type": "number"
                },
                {
                  "type": "null"
                }
              ],
              "default": null,
              "description": "Observer latitude in degrees (north positive). Omit to use place or the saved default.",
              "title": "Latitude"
            },
            "longitude": {
              "anyOf": [
                {
                  "maximum": 180,
                  "minimum": -180,
                  "type": "number"
                },
                {
                  "type": "null"
                }
              ],
              "default": null,
              "description": "Observer longitude in degrees (east positive). Omit to use place or the saved default.",
              "title": "Longitude"
            },
            "place": {
              "anyOf": [
                {
                  "type": "string"
                },
                {
                  "type": "null"
                }
              ],
              "default": null,
              "description": "Place name to observe from instead of coordinates, e.g. 'Moab, Utah'.",
              "title": "Place"
            }
          },
          "type": "object",
          "title": "get_jupiter_eventsArguments"
        },
        "name": "get_jupiter_events",
        "outputSchema": {
          "type": "object",
          "additionalProperties": true,
          "title": "get_jupiter_eventsDictOutput"
        }
      },
      {
        "annotations": {
          "idempotentHint": true,
          "openWorldHint": true,
          "readOnlyHint": true
        },
        "description": "Craters, mountains and other named features on the Moon's terminator at a given time.\n\nUse for 'what should I look at on the Moon tonight' or 'is Copernicus on the terminator'.\nThese are the features in low, raking sunlight, where shadows show the most relief. Lists\nthem largest first with the Sun's height at each and whether it is lunar sunrise or\nsunset there, plus the Moon's phase and terminator longitude. Feature names come from\nthe IAU/USGS gazetteer (downloaded once, about 24 MB).\n",
        "inputSchema": {
          "properties": {
            "time": {
              "anyOf": [
                {
                  "type": "string"
                },
                {
                  "type": "null"
                }
              ],
              "default": null,
              "description": "ISO 8601 time; without an offset it is the observer's local time. Omit for now.",
              "title": "Time"
            },
            "min_diameter_km": {
              "default": 20.0,
              "description": "Smallest feature to list",
              "maximum": 1000,
              "minimum": 0,
              "title": "Min Diameter Km",
              "type": "number"
            },
            "max_sun_altitude_deg": {
              "default": 8.0,
              "description": "How far from the terminator to look, as the Sun's height above the feature",
              "exclusiveMinimum": 0,
              "maximum": 30,
              "title": "Max Sun Altitude Deg",
              "type": "number"
            },
            "feature_types": {
              "anyOf": [
                {
                  "items": {
                    "enum": [
                      "crater",
                      "mare",
                      "mons",
                      "rima",
                      "vallis",
                      "rupes",
                      "dorsum",
                      "catena",
                      "lacus",
                      "sinus",
                      "palus",
                      "promontorium",
                      "oceanus"
                    ],
                    "type": "string"
                  },
                  "type": "array"
                },
                {
                  "type": "null"
                }
              ],
              "default": null,
              "description": "Restrict to these kinds of feature, e.g. ['crater'] or ['mons', 'rupes', 'vallis']",
              "title": "Feature Types"
            },
            "limit": {
              "default": 30,
              "description": "Maximum features",
              "maximum": 100,
              "minimum": 1,
              "title": "Limit",
              "type": "integer"
            },
            "latitude": {
              "anyOf": [
                {
                  "maximum": 90,
                  "minimum": -90,
                  "type": "number"
                },
                {
                  "type": "null"
                }
              ],
              "default": null,
              "description": "Observer latitude in degrees (north positive). Omit to use place or the saved default.",
              "title": "Latitude"
            },
            "longitude": {
              "anyOf": [
                {
                  "maximum": 180,
                  "minimum": -180,
                  "type": "number"
                },
                {
                  "type": "null"
                }
              ],
              "default": null,
              "description": "Observer longitude in degrees (east positive). Omit to use place or the saved default.",
              "title": "Longitude"
            },
            "place": {
              "anyOf": [
                {
                  "type": "string"
                },
                {
                  "type": "null"
                }
              ],
              "default": null,
              "description": "Place name to observe from instead of coordinates, e.g. 'Moab, Utah'.",
              "title": "Place"
            }
          },
          "type": "object",
          "title": "get_lunar_terminatorArguments"
        },
        "name": "get_lunar_terminator",
        "outputSchema": {
          "type": "object",
          "additionalProperties": true,
          "title": "get_lunar_terminatorDictOutput"
        }
      },
      {
        "annotations": {
          "idempotentHint": true,
          "openWorldHint": true,
          "readOnlyHint": true
        },
        "description": "How the Moon is tipped toward the observer, and which limb features that brings into view.\n\nUse for 'is Mare Orientale visible tonight', 'what is the libration' or 'which limb is\nfavoured'. Gives libration in longitude and latitude, the favoured limb, and for 45 limb\nfeatures (Mare Orientale, Mare Humboldtianum, Bailly, the polar craters and others) how far\ninside the limb each sits, whether it is sunlit and whether the view is favourable.\nComputed offline.\n",
        "inputSchema": {
          "properties": {
            "time": {
              "anyOf": [
                {
                  "type": "string"
                },
                {
                  "type": "null"
                }
              ],
              "default": null,
              "description": "ISO 8601 time; without an offset it is the observer's local time. Omit for now.",
              "title": "Time"
            },
            "latitude": {
              "anyOf": [
                {
                  "maximum": 90,
                  "minimum": -90,
                  "type": "number"
                },
                {
                  "type": "null"
                }
              ],
              "default": null,
              "description": "Observer latitude in degrees (north positive). Omit to use place or the saved default.",
              "title": "Latitude"
            },
            "longitude": {
              "anyOf": [
                {
                  "maximum": 180,
                  "minimum": -180,
                  "type": "number"
                },
                {
                  "type": "null"
                }
              ],
              "default": null,
              "description": "Observer longitude in degrees (east positive). Omit to use place or the saved default.",
              "title": "Longitude"
            },
            "place": {
              "anyOf": [
                {
                  "type": "string"
                },
                {
                  "type": "null"
                }
              ],
              "default": null,
              "description": "Place name to observe from instead of coordinates, e.g. 'Moab, Utah'.",
              "title": "Place"
            }
          },
          "type": "object",
          "title": "get_moon_librationArguments"
        },
        "name": "get_moon_libration",
        "outputSchema": {
          "type": "object",
          "additionalProperties": true,
          "title": "get_moon_librationDictOutput"
        }
      },
      {
        "annotations": {
          "idempotentHint": true,
          "openWorldHint": true,
          "readOnlyHint": true
        },
        "description": "Which comets are bright enough to see now, or how one comet will look over the coming weeks.\n\nUse for 'are there any comets visible', 'can I see comet X tonight' or 'when is comet X at\nits best'. Without a comet: the comets at or brighter than max_magnitude, brightest first,\nwith constellation, morning or evening sky, the equipment needed and, with a location, the\nbest time and altitude tonight. Brightness is from COBS observer reports where available,\notherwise JPL's prediction. With a comet: tonight's view plus a day-by-day trend (JPL\nHorizons). Comet brightness is hard to predict; present magnitudes as estimates.\n",
        "inputSchema": {
          "properties": {
            "comet": {
              "anyOf": [
                {
                  "type": "string"
                },
                {
                  "type": "null"
                }
              ],
              "default": null,
              "description": "A comet to look at, e.g. '12P', 'C/2025 R2', 'Tempel 2'. Omit to list the bright comets now.",
              "title": "Comet"
            },
            "max_magnitude": {
              "default": 12.0,
              "description": "Without a comet: only list comets at least this bright",
              "maximum": 18,
              "minimum": 0,
              "title": "Max Magnitude",
              "type": "number"
            },
            "limit": {
              "default": 10,
              "description": "Without a comet: maximum comets to list",
              "maximum": 30,
              "minimum": 1,
              "title": "Limit",
              "type": "integer"
            },
            "days": {
              "default": 30,
              "description": "With a comet: how many days of brightness and position trend",
              "maximum": 120,
              "minimum": 1,
              "title": "Days",
              "type": "integer"
            },
            "date": {
              "anyOf": [
                {
                  "type": "string"
                },
                {
                  "type": "null"
                }
              ],
              "default": null,
              "description": "Local date (YYYY-MM-DD) whose evening starts the night. Omit for tonight.",
              "title": "Date"
            },
            "latitude": {
              "anyOf": [
                {
                  "maximum": 90,
                  "minimum": -90,
                  "type": "number"
                },
                {
                  "type": "null"
                }
              ],
              "default": null,
              "description": "Observer latitude in degrees (north positive). Omit to use place or the saved default.",
              "title": "Latitude"
            },
            "longitude": {
              "anyOf": [
                {
                  "maximum": 180,
                  "minimum": -180,
                  "type": "number"
                },
                {
                  "type": "null"
                }
              ],
              "default": null,
              "description": "Observer longitude in degrees (east positive). Omit to use place or the saved default.",
              "title": "Longitude"
            },
            "place": {
              "anyOf": [
                {
                  "type": "string"
                },
                {
                  "type": "null"
                }
              ],
              "default": null,
              "description": "Place name to observe from instead of coordinates, e.g. 'Moab, Utah'.",
              "title": "Place"
            }
          },
          "type": "object",
          "title": "get_comet_visibilityArguments"
        },
        "name": "get_comet_visibility",
        "outputSchema": {
          "type": "object",
          "additionalProperties": true,
          "title": "get_comet_visibilityDictOutput"
        }
      },
      {
        "annotations": {
          "idempotentHint": true,
          "openWorldHint": true,
          "readOnlyHint": true
        },
        "description": "Asteroids bright enough for binoculars or a small telescope now, brightest first.\n\nUse for 'which asteroids can I see', 'is Vesta visible' or 'asteroids near opposition'.\nGives magnitude, constellation, how far from the Sun in the sky (near 180° means up all\nnight) and with a location the best time and altitude tonight. Positions and magnitudes\nfrom JPL Horizons; for a night-by-night table use get_asteroid_ephemeris.\n",
        "inputSchema": {
          "properties": {
            "max_magnitude": {
              "default": 10.0,
              "description": "Only asteroids at least this bright",
              "maximum": 12,
              "minimum": 4,
              "title": "Max Magnitude",
              "type": "number"
            },
            "limit": {
              "default": 10,
              "description": "Maximum asteroids",
              "maximum": 30,
              "minimum": 1,
              "title": "Limit",
              "type": "integer"
            },
            "date": {
              "anyOf": [
                {
                  "type": "string"
                },
                {
                  "type": "null"
                }
              ],
              "default": null,
              "description": "Local date (YYYY-MM-DD) whose evening starts the night. Omit for tonight.",
              "title": "Date"
            },
            "latitude": {
              "anyOf": [
                {
                  "maximum": 90,
                  "minimum": -90,
                  "type": "number"
                },
                {
                  "type": "null"
                }
              ],
              "default": null,
              "description": "Observer latitude in degrees (north positive). Omit to use place or the saved default.",
              "title": "Latitude"
            },
            "longitude": {
              "anyOf": [
                {
                  "maximum": 180,
                  "minimum": -180,
                  "type": "number"
                },
                {
                  "type": "null"
                }
              ],
              "default": null,
              "description": "Observer longitude in degrees (east positive). Omit to use place or the saved default.",
              "title": "Longitude"
            },
            "place": {
              "anyOf": [
                {
                  "type": "string"
                },
                {
                  "type": "null"
                }
              ],
              "default": null,
              "description": "Place name to observe from instead of coordinates, e.g. 'Moab, Utah'.",
              "title": "Place"
            }
          },
          "type": "object",
          "title": "find_bright_asteroidsArguments"
        },
        "name": "find_bright_asteroids",
        "outputSchema": {
          "type": "object",
          "additionalProperties": true,
          "title": "find_bright_asteroidsDictOutput"
        }
      },
      {
        "annotations": {
          "idempotentHint": true,
          "openWorldHint": true,
          "readOnlyHint": true
        },
        "description": "Where an asteroid (or comet) is and how bright, as a table over time, from JPL Horizons.\n\nUse for 'where is Vesta', 'how bright will Apophis get' or 'finder positions for asteroid X'.\nRows give RA/Dec, constellation, magnitude, motion across the sky, distances and elongation\nfrom the Sun; with a location, also altitude and direction. Also returns the object's\norbit class, size, albedo and whether it is a near-Earth or potentially hazardous object.\nUp to 500 rows.\n",
        "inputSchema": {
          "properties": {
            "target": {
              "description": "Asteroid or comet name, number or designation, e.g. 'Vesta', '4', 'Apophis', '2024 YR4', '12P'",
              "title": "Target",
              "type": "string"
            },
            "start": {
              "anyOf": [
                {
                  "type": "string"
                },
                {
                  "type": "null"
                }
              ],
              "default": null,
              "description": "First time, ISO 8601; without an offset it is the observer's local time. Omit for now.",
              "title": "Start"
            },
            "days": {
              "default": 7,
              "description": "How many days to cover",
              "exclusiveMinimum": 0,
              "maximum": 366,
              "title": "Days",
              "type": "number"
            },
            "step_hours": {
              "default": 24,
              "description": "Hours between rows (24 for daily)",
              "maximum": 720,
              "minimum": 0.25,
              "title": "Step Hours",
              "type": "number"
            },
            "latitude": {
              "anyOf": [
                {
                  "maximum": 90,
                  "minimum": -90,
                  "type": "number"
                },
                {
                  "type": "null"
                }
              ],
              "default": null,
              "description": "Observer latitude in degrees (north positive). Omit to use place or the saved default.",
              "title": "Latitude"
            },
            "longitude": {
              "anyOf": [
                {
                  "maximum": 180,
                  "minimum": -180,
                  "type": "number"
                },
                {
                  "type": "null"
                }
              ],
              "default": null,
              "description": "Observer longitude in degrees (east positive). Omit to use place or the saved default.",
              "title": "Longitude"
            },
            "place": {
              "anyOf": [
                {
                  "type": "string"
                },
                {
                  "type": "null"
                }
              ],
              "default": null,
              "description": "Place name to observe from instead of coordinates, e.g. 'Moab, Utah'.",
              "title": "Place"
            }
          },
          "required": [
            "target"
          ],
          "type": "object",
          "title": "get_asteroid_ephemerisArguments"
        },
        "name": "get_asteroid_ephemeris",
        "outputSchema": {
          "type": "object",
          "additionalProperties": true,
          "title": "get_asteroid_ephemerisDictOutput"
        }
      },
      {
        "annotations": {
          "idempotentHint": true,
          "openWorldHint": true,
          "readOnlyHint": true
        },
        "description": "Asteroids and comets passing close to Earth, in time order (JPL Close Approach Data).\n\nUse for 'any asteroids passing Earth this month', 'how close did X come' or 'next close\napproach of Apophis'. Gives time, distance in lunar distances and km, speed, absolute\nmagnitude and size. A location only adds local times. Whether one is observable needs\nget_asteroid_ephemeris.\n",
        "inputSchema": {
          "properties": {
            "start_date": {
              "anyOf": [
                {
                  "type": "string"
                },
                {
                  "type": "null"
                }
              ],
              "default": null,
              "description": "First day (YYYY-MM-DD), may be in the past; omit for now",
              "title": "Start Date"
            },
            "days": {
              "default": 60,
              "description": "How many days to search",
              "maximum": 3650,
              "minimum": 1,
              "title": "Days",
              "type": "integer"
            },
            "max_distance_lunar": {
              "default": 10,
              "description": "Only approaches closer than this many lunar distances (1 LD = 384,399 km)",
              "exclusiveMinimum": 0,
              "maximum": 200,
              "title": "Max Distance Lunar",
              "type": "number"
            },
            "max_absolute_magnitude": {
              "anyOf": [
                {
                  "maximum": 35,
                  "minimum": 5,
                  "type": "number"
                },
                {
                  "type": "null"
                }
              ],
              "default": null,
              "description": "Only objects with H at or below this (smaller H is bigger: H 22 is roughly 100-250 m)",
              "title": "Max Absolute Magnitude"
            },
            "limit": {
              "default": 25,
              "description": "Maximum approaches",
              "maximum": 100,
              "minimum": 1,
              "title": "Limit",
              "type": "integer"
            },
            "latitude": {
              "anyOf": [
                {
                  "maximum": 90,
                  "minimum": -90,
                  "type": "number"
                },
                {
                  "type": "null"
                }
              ],
              "default": null,
              "description": "Observer latitude in degrees (north positive). Omit to use place or the saved default.",
              "title": "Latitude"
            },
            "longitude": {
              "anyOf": [
                {
                  "maximum": 180,
                  "minimum": -180,
                  "type": "number"
                },
                {
                  "type": "null"
                }
              ],
              "default": null,
              "description": "Observer longitude in degrees (east positive). Omit to use place or the saved default.",
              "title": "Longitude"
            },
            "place": {
              "anyOf": [
                {
                  "type": "string"
                },
                {
                  "type": "null"
                }
              ],
              "default": null,
              "description": "Place name to observe from instead of coordinates, e.g. 'Moab, Utah'.",
              "title": "Place"
            }
          },
          "type": "object",
          "title": "find_close_approachesArguments"
        },
        "name": "find_close_approaches",
        "outputSchema": {
          "type": "object",
          "additionalProperties": true,
          "title": "find_close_approachesDictOutput"
        }
      },
      {
        "annotations": {
          "idempotentHint": true,
          "openWorldHint": true,
          "readOnlyHint": true
        },
        "description": "Large fireballs (bolides) detected by US government sensors, newest first (CNEOS).\n\nUse for 'was that huge fireball last night recorded', 'recent bolides near me' or 'how often\ndo big fireballs happen'. Gives time, position, altitude, speed and energy; with a location,\nthe distance and whether it was above the observer's horizon. Only metre-scale and larger\nimpacts are listed, and reports lag by days to weeks; ordinary bright meteors aren't here.\n",
        "inputSchema": {
          "properties": {
            "days": {
              "default": 365,
              "description": "How many days back to look",
              "maximum": 12000,
              "minimum": 1,
              "title": "Days",
              "type": "integer"
            },
            "limit": {
              "default": 20,
              "description": "Maximum events, newest first",
              "maximum": 100,
              "minimum": 1,
              "title": "Limit",
              "type": "integer"
            },
            "max_distance_km": {
              "anyOf": [
                {
                  "exclusiveMinimum": 0,
                  "maximum": 20000,
                  "type": "number"
                },
                {
                  "type": "null"
                }
              ],
              "default": null,
              "description": "Only events within this distance of the observer",
              "title": "Max Distance Km"
            },
            "latitude": {
              "anyOf": [
                {
                  "maximum": 90,
                  "minimum": -90,
                  "type": "number"
                },
                {
                  "type": "null"
                }
              ],
              "default": null,
              "description": "Observer latitude in degrees (north positive). Omit to use place or the saved default.",
              "title": "Latitude"
            },
            "longitude": {
              "anyOf": [
                {
                  "maximum": 180,
                  "minimum": -180,
                  "type": "number"
                },
                {
                  "type": "null"
                }
              ],
              "default": null,
              "description": "Observer longitude in degrees (east positive). Omit to use place or the saved default.",
              "title": "Longitude"
            },
            "place": {
              "anyOf": [
                {
                  "type": "string"
                },
                {
                  "type": "null"
                }
              ],
              "default": null,
              "description": "Place name to observe from instead of coordinates, e.g. 'Moab, Utah'.",
              "title": "Place"
            }
          },
          "type": "object",
          "title": "get_fireball_reportsArguments"
        },
        "name": "get_fireball_reports",
        "outputSchema": {
          "type": "object",
          "additionalProperties": true,
          "title": "get_fireball_reportsDictOutput"
        }
      },
      {
        "annotations": {
          "idempotentHint": true,
          "openWorldHint": true,
          "readOnlyHint": true
        },
        "description": "When the International Space Station will be visible from the observer's location.\n\nUse for 'when can I see the ISS' or 'is the space station going over tonight'. Lists passes\nwhere the ISS is sunlit against a dark sky: where it appears, its highest point and where it\nvanishes (often fading into Earth's shadow mid-sky), with local times to the second and an\nestimated magnitude. Computed from CelesTrak orbital elements with SGP4.\n",
        "inputSchema": {
          "properties": {
            "days": {
              "default": 5,
              "description": "How many days ahead (predictions drift after a few days)",
              "exclusiveMinimum": 0,
              "maximum": 10,
              "title": "Days",
              "type": "number"
            },
            "min_altitude": {
              "default": 10,
              "description": "Only count the satellite while at least this high, degrees",
              "maximum": 80,
              "minimum": 0,
              "title": "Min Altitude",
              "type": "number"
            },
            "latitude": {
              "anyOf": [
                {
                  "maximum": 90,
                  "minimum": -90,
                  "type": "number"
                },
                {
                  "type": "null"
                }
              ],
              "default": null,
              "description": "Observer latitude in degrees (north positive). Omit to use place or the saved default.",
              "title": "Latitude"
            },
            "longitude": {
              "anyOf": [
                {
                  "maximum": 180,
                  "minimum": -180,
                  "type": "number"
                },
                {
                  "type": "null"
                }
              ],
              "default": null,
              "description": "Observer longitude in degrees (east positive). Omit to use place or the saved default.",
              "title": "Longitude"
            },
            "place": {
              "anyOf": [
                {
                  "type": "string"
                },
                {
                  "type": "null"
                }
              ],
              "default": null,
              "description": "Place name to observe from instead of coordinates, e.g. 'Moab, Utah'.",
              "title": "Place"
            }
          },
          "type": "object",
          "title": "get_iss_passesArguments"
        },
        "name": "get_iss_passes",
        "outputSchema": {
          "type": "object",
          "additionalProperties": true,
          "title": "get_iss_passesDictOutput"
        }
      },
      {
        "annotations": {
          "idempotentHint": true,
          "openWorldHint": true,
          "readOnlyHint": true
        },
        "description": "Upcoming passes of any Earth satellite over the observer, by name or NORAD number.\n\nUse for 'when does Hubble pass over', 'Tiangong passes this week' or a specific NORAD id.\nBy default only visible passes (satellite sunlit, observer's sky dark), with where it\nappears, peaks and vanishes. Brightness is estimated for the ISS, Tiangong, Hubble and\nStarlink, or any satellite given standard_magnitude. For the ISS, get_iss_passes is simpler.\n",
        "inputSchema": {
          "properties": {
            "satellite": {
              "description": "NORAD catalog number, a common name ('ISS', 'Tiangong', 'Hubble') or a CelesTrak name ('STARLINK-1234', 'NOAA 19')",
              "title": "Satellite",
              "type": "string"
            },
            "days": {
              "default": 5,
              "description": "How many days ahead (predictions drift after a few days)",
              "exclusiveMinimum": 0,
              "maximum": 10,
              "title": "Days",
              "type": "number"
            },
            "min_altitude": {
              "default": 10,
              "description": "Only count the satellite while at least this high, degrees",
              "maximum": 80,
              "minimum": 0,
              "title": "Min Altitude",
              "type": "number"
            },
            "include_daylight": {
              "default": false,
              "description": "Also list passes that can't be seen (daylight or Earth's shadow), e.g. for radio",
              "title": "Include Daylight",
              "type": "boolean"
            },
            "standard_magnitude": {
              "anyOf": [
                {
                  "maximum": 15,
                  "minimum": -5,
                  "type": "number"
                },
                {
                  "type": "null"
                }
              ],
              "default": null,
              "description": "Satellite's magnitude at 1000 km and half phase, if known; enables brightness estimates",
              "title": "Standard Magnitude"
            },
            "latitude": {
              "anyOf": [
                {
                  "maximum": 90,
                  "minimum": -90,
                  "type": "number"
                },
                {
                  "type": "null"
                }
              ],
              "default": null,
              "description": "Observer latitude in degrees (north positive). Omit to use place or the saved default.",
              "title": "Latitude"
            },
            "longitude": {
              "anyOf": [
                {
                  "maximum": 180,
                  "minimum": -180,
                  "type": "number"
                },
                {
                  "type": "null"
                }
              ],
              "default": null,
              "description": "Observer longitude in degrees (east positive). Omit to use place or the saved default.",
              "title": "Longitude"
            },
            "place": {
              "anyOf": [
                {
                  "type": "string"
                },
                {
                  "type": "null"
                }
              ],
              "default": null,
              "description": "Place name to observe from instead of coordinates, e.g. 'Moab, Utah'.",
              "title": "Place"
            }
          },
          "required": [
            "satellite"
          ],
          "type": "object",
          "title": "get_satellite_passesArguments"
        },
        "name": "get_satellite_passes",
        "outputSchema": {
          "type": "object",
          "additionalProperties": true,
          "title": "get_satellite_passesDictOutput"
        }
      },
      {
        "annotations": {
          "idempotentHint": true,
          "openWorldHint": true,
          "readOnlyHint": true
        },
        "description": "Satellites above the observer right now (or at a given time): where each is and where it's heading.\n\nUse for 'what is that moving light' or 'what satellites are up now'. Lists each satellite's\naltitude, direction, distance, whether it is lit by the Sun, estimated magnitude where known,\nand where it will leave view (setting or fading into Earth's shadow). Brightest first.\n",
        "inputSchema": {
          "properties": {
            "time": {
              "anyOf": [
                {
                  "type": "string"
                },
                {
                  "type": "null"
                }
              ],
              "default": null,
              "description": "ISO 8601 time; without an offset it is the observer's local time. Omit for now.",
              "title": "Time"
            },
            "group": {
              "default": "visual",
              "description": "Which satellites: visual (about 150 of the brightest), stations, starlink, or active (all ~16,000; slower first download)",
              "enum": [
                "visual",
                "stations",
                "starlink",
                "active"
              ],
              "title": "Group",
              "type": "string"
            },
            "min_altitude": {
              "default": 10,
              "description": "Only count the satellite while at least this high, degrees",
              "maximum": 80,
              "minimum": 0,
              "title": "Min Altitude",
              "type": "number"
            },
            "visible_only": {
              "default": true,
              "description": "Only satellites that are sunlit while the observer's sky is dark",
              "title": "Visible Only",
              "type": "boolean"
            },
            "limit": {
              "default": 25,
              "description": "Maximum satellites",
              "maximum": 200,
              "minimum": 1,
              "title": "Limit",
              "type": "integer"
            },
            "latitude": {
              "anyOf": [
                {
                  "maximum": 90,
                  "minimum": -90,
                  "type": "number"
                },
                {
                  "type": "null"
                }
              ],
              "default": null,
              "description": "Observer latitude in degrees (north positive). Omit to use place or the saved default.",
              "title": "Latitude"
            },
            "longitude": {
              "anyOf": [
                {
                  "maximum": 180,
                  "minimum": -180,
                  "type": "number"
                },
                {
                  "type": "null"
                }
              ],
              "default": null,
              "description": "Observer longitude in degrees (east positive). Omit to use place or the saved default.",
              "title": "Longitude"
            },
            "place": {
              "anyOf": [
                {
                  "type": "string"
                },
                {
                  "type": "null"
                }
              ],
              "default": null,
              "description": "Place name to observe from instead of coordinates, e.g. 'Moab, Utah'.",
              "title": "Place"
            }
          },
          "type": "object",
          "title": "find_satellites_overheadArguments"
        },
        "name": "find_satellites_overhead",
        "outputSchema": {
          "type": "object",
          "additionalProperties": true,
          "title": "find_satellites_overheadDictOutput"
        }
      },
      {
        "annotations": {
          "idempotentHint": true,
          "openWorldHint": true,
          "readOnlyHint": true
        },
        "description": "When the ISS (or another satellite) crosses the face of the Sun or Moon near the observer.\n\nUse for 'can I photograph the ISS crossing the Moon' or 'any ISS solar transits near me'.\nA transit is seen only within a few kilometres of a centerline, so each event gives the\nnearest point on that line (distance, direction, coordinates), the path width, the time to\nthe millisecond, how long the crossing lasts (about a second), and whether it transits\nfrom the observer's own spot. Predictions shift by kilometres as orbits change; recheck a\nday before. Solar transits need a proper solar filter.\n",
        "inputSchema": {
          "properties": {
            "days": {
              "default": 7,
              "description": "How many days ahead (predictions drift after a few days)",
              "exclusiveMinimum": 0,
              "maximum": 10,
              "title": "Days",
              "type": "number"
            },
            "max_distance_km": {
              "default": 50,
              "description": "How far you would travel to the centerline",
              "exclusiveMinimum": 0,
              "maximum": 300,
              "title": "Max Distance Km",
              "type": "number"
            },
            "bodies": {
              "anyOf": [
                {
                  "items": {
                    "enum": [
                      "Sun",
                      "Moon"
                    ],
                    "type": "string"
                  },
                  "type": "array"
                },
                {
                  "type": "null"
                }
              ],
              "default": null,
              "description": "Sun, Moon or both (default)",
              "title": "Bodies"
            },
            "min_altitude": {
              "default": 10,
              "description": "Lowest Sun or Moon altitude worth considering, degrees",
              "maximum": 80,
              "minimum": 0,
              "title": "Min Altitude",
              "type": "number"
            },
            "satellite": {
              "default": "ISS",
              "description": "Satellite to check; the ISS by default, or 'Tiangong', a name or a NORAD number",
              "title": "Satellite",
              "type": "string"
            },
            "latitude": {
              "anyOf": [
                {
                  "maximum": 90,
                  "minimum": -90,
                  "type": "number"
                },
                {
                  "type": "null"
                }
              ],
              "default": null,
              "description": "Observer latitude in degrees (north positive). Omit to use place or the saved default.",
              "title": "Latitude"
            },
            "longitude": {
              "anyOf": [
                {
                  "maximum": 180,
                  "minimum": -180,
                  "type": "number"
                },
                {
                  "type": "null"
                }
              ],
              "default": null,
              "description": "Observer longitude in degrees (east positive). Omit to use place or the saved default.",
              "title": "Longitude"
            },
            "place": {
              "anyOf": [
                {
                  "type": "string"
                },
                {
                  "type": "null"
                }
              ],
              "default": null,
              "description": "Place name to observe from instead of coordinates, e.g. 'Moab, Utah'.",
              "title": "Place"
            }
          },
          "type": "object",
          "title": "predict_iss_transitArguments"
        },
        "name": "predict_iss_transit",
        "outputSchema": {
          "type": "object",
          "additionalProperties": true,
          "title": "predict_iss_transitDictOutput"
        }
      },
      {
        "annotations": {
          "idempotentHint": true,
          "openWorldHint": true,
          "readOnlyHint": true
        },
        "description": "Recently launched Starlink batches and when their 'train' of satellites passes over.\n\nUse for 'I saw a line of lights moving across the sky' or 'when can I see a Starlink\ntrain'. For each batch launched in the last few weeks: satellite count, altitude, how\nstretched out the line is, and visible passes with times for the first and last satellite.\nTrains are best in the first days after launch and disperse within a few weeks.\n",
        "inputSchema": {
          "properties": {
            "days": {
              "default": 3,
              "description": "How many days ahead to look for passes",
              "exclusiveMinimum": 0,
              "maximum": 7,
              "title": "Days",
              "type": "number"
            },
            "max_launch_age_days": {
              "default": 21,
              "description": "Only batches launched within this many days",
              "exclusiveMinimum": 0,
              "maximum": 30,
              "title": "Max Launch Age Days",
              "type": "number"
            },
            "min_altitude": {
              "default": 10,
              "description": "Only count the satellite while at least this high, degrees",
              "maximum": 80,
              "minimum": 0,
              "title": "Min Altitude",
              "type": "number"
            },
            "latitude": {
              "anyOf": [
                {
                  "maximum": 90,
                  "minimum": -90,
                  "type": "number"
                },
                {
                  "type": "null"
                }
              ],
              "default": null,
              "description": "Observer latitude in degrees (north positive). Omit to use place or the saved default.",
              "title": "Latitude"
            },
            "longitude": {
              "anyOf": [
                {
                  "maximum": 180,
                  "minimum": -180,
                  "type": "number"
                },
                {
                  "type": "null"
                }
              ],
              "default": null,
              "description": "Observer longitude in degrees (east positive). Omit to use place or the saved default.",
              "title": "Longitude"
            },
            "place": {
              "anyOf": [
                {
                  "type": "string"
                },
                {
                  "type": "null"
                }
              ],
              "default": null,
              "description": "Place name to observe from instead of coordinates, e.g. 'Moab, Utah'.",
              "title": "Place"
            }
          },
          "type": "object",
          "title": "get_starlink_trainsArguments"
        },
        "name": "get_starlink_trains",
        "outputSchema": {
          "type": "object",
          "additionalProperties": true,
          "title": "get_starlink_trainsDictOutput"
        }
      },
      {
        "annotations": {
          "idempotentHint": true,
          "openWorldHint": true,
          "readOnlyHint": true
        },
        "description": "Every catalogued pair in a double or multiple star, and whether a telescope can split each.\n\nUse for 'can my 4-inch split epsilon Lyrae', 'how far apart are Albireo's stars' or 'what\nare the components of Castor'. From the Washington Double Star catalog: separation and\nposition angle at the latest measurement, magnitudes and spectral types; with an aperture,\na split verdict (easy/moderate/challenging) and a magnification to try.\n",
        "inputSchema": {
          "properties": {
            "name": {
              "description": "Star name ('Albireo', 'epsilon Lyrae', 'Mizar'), WDS id ('19307+2758') or discoverer designation ('STF 2382')",
              "title": "Name",
              "type": "string"
            },
            "aperture_mm": {
              "anyOf": [
                {
                  "exclusiveMinimum": 0,
                  "maximum": 2000,
                  "type": "number"
                },
                {
                  "type": "null"
                }
              ],
              "default": null,
              "description": "Telescope aperture in mm, to judge whether each pair can be split",
              "title": "Aperture Mm"
            },
            "seeing_arcsec": {
              "default": 2.0,
              "description": "Typical seeing (star blur) in arcseconds: 1 excellent, 2 average, 3-4 poor",
              "maximum": 6,
              "minimum": 0.3,
              "title": "Seeing Arcsec",
              "type": "number"
            }
          },
          "required": [
            "name"
          ],
          "type": "object",
          "title": "get_double_starArguments"
        },
        "name": "get_double_star",
        "outputSchema": {
          "type": "object",
          "additionalProperties": true,
          "title": "get_double_starDictOutput"
        }
      },
      {
        "annotations": {
          "idempotentHint": true,
          "openWorldHint": true,
          "readOnlyHint": true
        },
        "description": "Double stars a given telescope can split, brightest first, optionally just tonight's.\n\nUse for 'good double stars for my 6-inch tonight' or 'a challenging double for a 4-inch'.\nSearches the Washington Double Star catalog for pairs above the Dawes limit and the seeing,\nallowing for brightness differences, and names each primary from SIMBAD.\n",
        "inputSchema": {
          "properties": {
            "aperture_mm": {
              "default": 100,
              "description": "Telescope aperture in mm",
              "exclusiveMinimum": 0,
              "maximum": 2000,
              "title": "Aperture Mm",
              "type": "number"
            },
            "seeing_arcsec": {
              "default": 2.0,
              "description": "Typical seeing (star blur) in arcseconds: 1 excellent, 2 average, 3-4 poor",
              "maximum": 6,
              "minimum": 0.3,
              "title": "Seeing Arcsec",
              "type": "number"
            },
            "max_primary_magnitude": {
              "default": 6.5,
              "description": "Only pairs whose brighter star is at least this bright",
              "maximum": 10,
              "minimum": -2,
              "title": "Max Primary Magnitude",
              "type": "number"
            },
            "max_separation_arcsec": {
              "default": 60,
              "description": "Skip pairs wider than this",
              "exclusiveMinimum": 0,
              "maximum": 300,
              "title": "Max Separation Arcsec",
              "type": "number"
            },
            "constellation": {
              "anyOf": [
                {
                  "type": "string"
                },
                {
                  "type": "null"
                }
              ],
              "default": null,
              "description": "Only pairs in this constellation (name or abbreviation)",
              "title": "Constellation"
            },
            "challenging_only": {
              "default": false,
              "description": "Only pairs near the telescope's limit, as a test",
              "title": "Challenging Only",
              "type": "boolean"
            },
            "visible_tonight": {
              "default": true,
              "description": "Only pairs that climb above min_altitude in tonight's dark sky (needs a location)",
              "title": "Visible Tonight",
              "type": "boolean"
            },
            "min_altitude": {
              "default": 25.0,
              "description": "Minimum useful altitude in degrees",
              "maximum": 80,
              "minimum": 0,
              "title": "Min Altitude",
              "type": "number"
            },
            "date": {
              "anyOf": [
                {
                  "type": "string"
                },
                {
                  "type": "null"
                }
              ],
              "default": null,
              "description": "Local date (YYYY-MM-DD) whose evening starts the night. Omit for tonight.",
              "title": "Date"
            },
            "latitude": {
              "anyOf": [
                {
                  "maximum": 90,
                  "minimum": -90,
                  "type": "number"
                },
                {
                  "type": "null"
                }
              ],
              "default": null,
              "description": "Observer latitude in degrees (north positive). Omit to use place or the saved default.",
              "title": "Latitude"
            },
            "longitude": {
              "anyOf": [
                {
                  "maximum": 180,
                  "minimum": -180,
                  "type": "number"
                },
                {
                  "type": "null"
                }
              ],
              "default": null,
              "description": "Observer longitude in degrees (east positive). Omit to use place or the saved default.",
              "title": "Longitude"
            },
            "place": {
              "anyOf": [
                {
                  "type": "string"
                },
                {
                  "type": "null"
                }
              ],
              "default": null,
              "description": "Place name to observe from instead of coordinates, e.g. 'Moab, Utah'.",
              "title": "Place"
            },
            "limit": {
              "default": 20,
              "description": "Maximum pairs",
              "maximum": 50,
              "minimum": 1,
              "title": "Limit",
              "type": "integer"
            }
          },
          "type": "object",
          "title": "find_splittable_doublesArguments"
        },
        "name": "find_splittable_doubles",
        "outputSchema": {
          "type": "object",
          "additionalProperties": true,
          "title": "find_splittable_doublesDictOutput"
        }
      },
      {
        "annotations": {
          "idempotentHint": true,
          "openWorldHint": true,
          "readOnlyHint": true
        },
        "description": "How bright a variable star is right now, from recent AAVSO observations.\n\nUse for 'is SS Cyg in outburst', 'how bright is Mira now', 'when is Algol's next eclipse' or\n'is chi Cygni near maximum'. Gives the latest observation, medians by band over the last week,\nthe recent trend, where it sits in its range, and predicted maxima or eclipses from the period.\n",
        "inputSchema": {
          "properties": {
            "name": {
              "description": "Variable star name: 'Mira', 'R Leo', 'SS Cyg', 'Algol', 'chi Cyg'",
              "title": "Name",
              "type": "string"
            },
            "days": {
              "default": 30,
              "description": "How many days of observations to summarise",
              "maximum": 365,
              "minimum": 1,
              "title": "Days",
              "type": "integer"
            },
            "latitude": {
              "anyOf": [
                {
                  "maximum": 90,
                  "minimum": -90,
                  "type": "number"
                },
                {
                  "type": "null"
                }
              ],
              "default": null,
              "description": "Observer latitude in degrees (north positive). Omit to use place or the saved default.",
              "title": "Latitude"
            },
            "longitude": {
              "anyOf": [
                {
                  "maximum": 180,
                  "minimum": -180,
                  "type": "number"
                },
                {
                  "type": "null"
                }
              ],
              "default": null,
              "description": "Observer longitude in degrees (east positive). Omit to use place or the saved default.",
              "title": "Longitude"
            },
            "place": {
              "anyOf": [
                {
                  "type": "string"
                },
                {
                  "type": "null"
                }
              ],
              "default": null,
              "description": "Place name to observe from instead of coordinates, e.g. 'Moab, Utah'.",
              "title": "Place"
            }
          },
          "required": [
            "name"
          ],
          "type": "object",
          "title": "get_variable_star_statusArguments"
        },
        "name": "get_variable_star_status",
        "outputSchema": {
          "type": "object",
          "additionalProperties": true,
          "title": "get_variable_star_statusDictOutput"
        }
      },
      {
        "annotations": {
          "idempotentHint": true,
          "openWorldHint": true,
          "readOnlyHint": true
        },
        "description": "A variable star's light curve from AAVSO observations, binned by band.\n\nUse for 'plot Mira's brightness this year', 'how did SS Cyg behave lately' or to compare a\nstar's cycle with its prediction. Each point is the median magnitude in a time bin, with\nthe count of observations; up to two years.\n",
        "inputSchema": {
          "properties": {
            "name": {
              "description": "Variable star name, e.g. 'Mira', 'SS Cyg', 'R CrB'",
              "title": "Name",
              "type": "string"
            },
            "days": {
              "default": 365,
              "description": "How many days back",
              "maximum": 730,
              "minimum": 1,
              "title": "Days",
              "type": "integer"
            },
            "bands": {
              "anyOf": [
                {
                  "items": {
                    "type": "string"
                  },
                  "type": "array"
                },
                {
                  "type": "null"
                }
              ],
              "default": null,
              "description": "Only these AAVSO bands, e.g. ['Vis.', 'V']; omit for all",
              "title": "Bands"
            },
            "bin_days": {
              "anyOf": [
                {
                  "exclusiveMinimum": 0,
                  "maximum": 60,
                  "type": "number"
                },
                {
                  "type": "null"
                }
              ],
              "default": null,
              "description": "Bin width in days; omit to get about 150 points",
              "title": "Bin Days"
            },
            "latitude": {
              "anyOf": [
                {
                  "maximum": 90,
                  "minimum": -90,
                  "type": "number"
                },
                {
                  "type": "null"
                }
              ],
              "default": null,
              "description": "Observer latitude in degrees (north positive). Omit to use place or the saved default.",
              "title": "Latitude"
            },
            "longitude": {
              "anyOf": [
                {
                  "maximum": 180,
                  "minimum": -180,
                  "type": "number"
                },
                {
                  "type": "null"
                }
              ],
              "default": null,
              "description": "Observer longitude in degrees (east positive). Omit to use place or the saved default.",
              "title": "Longitude"
            },
            "place": {
              "anyOf": [
                {
                  "type": "string"
                },
                {
                  "type": "null"
                }
              ],
              "default": null,
              "description": "Place name to observe from instead of coordinates, e.g. 'Moab, Utah'.",
              "title": "Place"
            }
          },
          "required": [
            "name"
          ],
          "type": "object",
          "title": "get_light_curveArguments"
        },
        "name": "get_light_curve",
        "outputSchema": {
          "type": "object",
          "additionalProperties": true,
          "title": "get_light_curveDictOutput"
        }
      },
      {
        "annotations": {
          "idempotentHint": true,
          "openWorldHint": true,
          "readOnlyHint": true
        },
        "description": "Supernovae currently bright enough for amateur telescopes, brightest first.\n\nUse for 'any bright supernovae right now', 'is there a supernova in M101' or 'what can I\nimage tonight'. Gives type, host galaxy, position, latest and peak magnitude with dates,\ndiscovery date and discoverer, and with a location the best time tonight.\n",
        "inputSchema": {
          "properties": {
            "max_magnitude": {
              "default": 16.0,
              "description": "Only supernovae at least this bright",
              "maximum": 17,
              "minimum": 8,
              "title": "Max Magnitude",
              "type": "number"
            },
            "limit": {
              "default": 15,
              "description": "Maximum supernovae",
              "maximum": 50,
              "minimum": 1,
              "title": "Limit",
              "type": "integer"
            },
            "include_candidates": {
              "default": false,
              "description": "Also list unconfirmed supernova candidates found by the ALeRCE broker in ZTF data (mostly fainter than 17)",
              "title": "Include Candidates",
              "type": "boolean"
            },
            "candidate_days": {
              "default": 10,
              "description": "With candidates: first detected within this many days",
              "maximum": 60,
              "minimum": 1,
              "title": "Candidate Days",
              "type": "integer"
            },
            "min_altitude": {
              "default": 20.0,
              "description": "Minimum useful altitude in degrees",
              "maximum": 80,
              "minimum": 0,
              "title": "Min Altitude",
              "type": "number"
            },
            "date": {
              "anyOf": [
                {
                  "type": "string"
                },
                {
                  "type": "null"
                }
              ],
              "default": null,
              "description": "Local date (YYYY-MM-DD) whose evening starts the night. Omit for tonight.",
              "title": "Date"
            },
            "latitude": {
              "anyOf": [
                {
                  "maximum": 90,
                  "minimum": -90,
                  "type": "number"
                },
                {
                  "type": "null"
                }
              ],
              "default": null,
              "description": "Observer latitude in degrees (north positive). Omit to use place or the saved default.",
              "title": "Latitude"
            },
            "longitude": {
              "anyOf": [
                {
                  "maximum": 180,
                  "minimum": -180,
                  "type": "number"
                },
                {
                  "type": "null"
                }
              ],
              "default": null,
              "description": "Observer longitude in degrees (east positive). Omit to use place or the saved default.",
              "title": "Longitude"
            },
            "place": {
              "anyOf": [
                {
                  "type": "string"
                },
                {
                  "type": "null"
                }
              ],
              "default": null,
              "description": "Place name to observe from instead of coordinates, e.g. 'Moab, Utah'.",
              "title": "Place"
            }
          },
          "type": "object",
          "title": "get_recent_supernovaeArguments"
        },
        "name": "get_recent_supernovae",
        "outputSchema": {
          "type": "object",
          "additionalProperties": true,
          "title": "get_recent_supernovaeDictOutput"
        }
      },
      {
        "annotations": {
          "idempotentHint": true,
          "openWorldHint": true,
          "readOnlyHint": true
        },
        "description": "Recent novae in our Galaxy, with peak and current brightness, newest first.\n\nUse for 'is there a nova visible now' or 'how bright is Nova Sagittae'. Lists novae from\nKoji Mukai's list with discovery date, peak magnitude, the latest AAVSO magnitude and with a\nlocation whether it is up tonight.\n",
        "inputSchema": {
          "properties": {
            "days": {
              "default": 120,
              "description": "Discovered within this many days",
              "maximum": 730,
              "minimum": 1,
              "title": "Days",
              "type": "integer"
            },
            "include_extragalactic": {
              "default": false,
              "description": "Also list novae in other galaxies, mostly M31 (magnitude 15-19)",
              "title": "Include Extragalactic",
              "type": "boolean"
            },
            "min_altitude": {
              "default": 15.0,
              "description": "Minimum useful altitude in degrees",
              "maximum": 80,
              "minimum": 0,
              "title": "Min Altitude",
              "type": "number"
            },
            "date": {
              "anyOf": [
                {
                  "type": "string"
                },
                {
                  "type": "null"
                }
              ],
              "default": null,
              "description": "Local date (YYYY-MM-DD) whose evening starts the night. Omit for tonight.",
              "title": "Date"
            },
            "latitude": {
              "anyOf": [
                {
                  "maximum": 90,
                  "minimum": -90,
                  "type": "number"
                },
                {
                  "type": "null"
                }
              ],
              "default": null,
              "description": "Observer latitude in degrees (north positive). Omit to use place or the saved default.",
              "title": "Latitude"
            },
            "longitude": {
              "anyOf": [
                {
                  "maximum": 180,
                  "minimum": -180,
                  "type": "number"
                },
                {
                  "type": "null"
                }
              ],
              "default": null,
              "description": "Observer longitude in degrees (east positive). Omit to use place or the saved default.",
              "title": "Longitude"
            },
            "place": {
              "anyOf": [
                {
                  "type": "string"
                },
                {
                  "type": "null"
                }
              ],
              "default": null,
              "description": "Place name to observe from instead of coordinates, e.g. 'Moab, Utah'.",
              "title": "Place"
            }
          },
          "type": "object",
          "title": "get_novaeArguments"
        },
        "name": "get_novae",
        "outputSchema": {
          "type": "object",
          "additionalProperties": true,
          "title": "get_novaeDictOutput"
        }
      },
      {
        "annotations": {
          "idempotentHint": true,
          "openWorldHint": true,
          "readOnlyHint": true
        },
        "description": "Which spacecraft NASA's Deep Space Network is talking to right now.\n\nUse for 'is anyone talking to Voyager', 'what is the DSN doing' or 'how far away is Juno'.\nLists each spacecraft in contact, the antennas, distance and light time, and whether data\nor commands are flowing. Live from DSN Now; contacts change every few hours.\n",
        "inputSchema": {
          "properties": {
            "spacecraft": {
              "anyOf": [
                {
                  "type": "string"
                },
                {
                  "type": "null"
                }
              ],
              "default": null,
              "description": "Only contacts with this spacecraft, e.g. 'Voyager', 'JWST', 'Juno'",
              "title": "Spacecraft"
            },
            "include_antennas": {
              "default": false,
              "description": "Also list every antenna at Goldstone, Madrid and Canberra with its activity and pointing",
              "title": "Include Antennas",
              "type": "boolean"
            }
          },
          "type": "object",
          "title": "get_dsn_statusArguments"
        },
        "name": "get_dsn_status",
        "outputSchema": {
          "type": "object",
          "additionalProperties": true,
          "title": "get_dsn_statusDictOutput"
        }
      },
      {
        "annotations": {
          "idempotentHint": true,
          "openWorldHint": true,
          "readOnlyHint": true
        },
        "description": "Facts about a known exoplanet, or all planets of a host star, from the NASA Exoplanet Archive.\n\nUse for 'tell me about TRAPPIST-1 e', 'how big is HD 209458 b' or 'what planets orbit\nKepler-90'. Gives discovery, orbit, radius, mass, temperature, insolation, the host star and\nits distance; for transiting planets, the next few transit times with their uncertainty.\n",
        "inputSchema": {
          "properties": {
            "name": {
              "description": "Planet name ('TRAPPIST-1 e', 'HD 189733 b') or host star name to list its planets ('TRAPPIST-1', 'Kepler-22')",
              "title": "Name",
              "type": "string"
            },
            "latitude": {
              "anyOf": [
                {
                  "maximum": 90,
                  "minimum": -90,
                  "type": "number"
                },
                {
                  "type": "null"
                }
              ],
              "default": null,
              "description": "Observer latitude in degrees (north positive). Omit to use place or the saved default.",
              "title": "Latitude"
            },
            "longitude": {
              "anyOf": [
                {
                  "maximum": 180,
                  "minimum": -180,
                  "type": "number"
                },
                {
                  "type": "null"
                }
              ],
              "default": null,
              "description": "Observer longitude in degrees (east positive). Omit to use place or the saved default.",
              "title": "Longitude"
            },
            "place": {
              "anyOf": [
                {
                  "type": "string"
                },
                {
                  "type": "null"
                }
              ],
              "default": null,
              "description": "Place name to observe from instead of coordinates, e.g. 'Moab, Utah'.",
              "title": "Place"
            }
          },
          "required": [
            "name"
          ],
          "type": "object",
          "title": "get_exoplanetArguments"
        },
        "name": "get_exoplanet",
        "outputSchema": {
          "type": "object",
          "additionalProperties": true,
          "title": "get_exoplanetDictOutput"
        }
      },
      {
        "annotations": {
          "idempotentHint": true,
          "openWorldHint": true,
          "readOnlyHint": true
        },
        "description": "Find exoplanets by size, distance, starlight received, discovery method or year.\n\nUse for 'nearest Earth-sized planets', 'planets in the habitable zone within 50 light years'\nor 'exoplanets found by direct imaging'. Returns the total number of matches and the top\nresults with radius, mass, temperature, insolation and distance.\n",
        "inputSchema": {
          "properties": {
            "discovery_method": {
              "anyOf": [
                {
                  "type": "string"
                },
                {
                  "type": "null"
                }
              ],
              "default": null,
              "description": "e.g. 'Transit', 'Radial Velocity', 'Imaging', 'Microlensing'",
              "title": "Discovery Method"
            },
            "min_radius_earth": {
              "anyOf": [
                {
                  "exclusiveMinimum": 0,
                  "type": "number"
                },
                {
                  "type": "null"
                }
              ],
              "default": null,
              "description": "Smallest planet radius, Earth radii",
              "title": "Min Radius Earth"
            },
            "max_radius_earth": {
              "anyOf": [
                {
                  "exclusiveMinimum": 0,
                  "type": "number"
                },
                {
                  "type": "null"
                }
              ],
              "default": null,
              "description": "Largest planet radius, Earth radii",
              "title": "Max Radius Earth"
            },
            "max_distance_pc": {
              "anyOf": [
                {
                  "exclusiveMinimum": 0,
                  "type": "number"
                },
                {
                  "type": "null"
                }
              ],
              "default": null,
              "description": "Only systems within this distance (1 pc = 3.26 light years)",
              "title": "Max Distance Pc"
            },
            "min_insolation": {
              "anyOf": [
                {
                  "minimum": 0,
                  "type": "number"
                },
                {
                  "type": "null"
                }
              ],
              "default": null,
              "description": "Least starlight received, relative to Earth (Earth = 1)",
              "title": "Min Insolation"
            },
            "max_insolation": {
              "anyOf": [
                {
                  "minimum": 0,
                  "type": "number"
                },
                {
                  "type": "null"
                }
              ],
              "default": null,
              "description": "Most starlight received, relative to Earth; about 0.35-1.75 is a rough habitable range",
              "title": "Max Insolation"
            },
            "max_host_magnitude": {
              "anyOf": [
                {
                  "type": "number"
                },
                {
                  "type": "null"
                }
              ],
              "default": null,
              "description": "Only host stars at least this bright (V)",
              "title": "Max Host Magnitude"
            },
            "transiting_only": {
              "default": false,
              "description": "Only planets seen to transit their star",
              "title": "Transiting Only",
              "type": "boolean"
            },
            "discovered_since": {
              "anyOf": [
                {
                  "maximum": 2100,
                  "minimum": 1989,
                  "type": "integer"
                },
                {
                  "type": "null"
                }
              ],
              "default": null,
              "description": "Discovered in or after this year",
              "title": "Discovered Since"
            },
            "sort_by": {
              "default": "distance",
              "description": "Order of results",
              "enum": [
                "distance",
                "radius",
                "mass",
                "newest",
                "host_brightness",
                "period"
              ],
              "title": "Sort By",
              "type": "string"
            },
            "limit": {
              "default": 20,
              "description": "Maximum planets",
              "maximum": 100,
              "minimum": 1,
              "title": "Limit",
              "type": "integer"
            }
          },
          "type": "object",
          "title": "search_exoplanetsArguments"
        },
        "name": "search_exoplanets",
        "outputSchema": {
          "type": "object",
          "additionalProperties": true,
          "title": "search_exoplanetsDictOutput"
        }
      },
      {
        "annotations": {
          "idempotentHint": true,
          "openWorldHint": true,
          "readOnlyHint": true
        },
        "description": "Exoplanet transits observable from the location tonight, in time order.\n\nUse for 'which exoplanet transits can I record tonight' or planning transit photometry.\nGives ingress, mid-transit and egress in local time (converted from the archive's barycentric\nephemeris), depth in percent and millimagnitudes, the host star's brightness, altitudes during\nthe transit, and the timing uncertainty from the ephemeris.\n",
        "inputSchema": {
          "properties": {
            "max_host_magnitude": {
              "default": 12.0,
              "description": "Only host stars at least this bright (V)",
              "maximum": 13,
              "minimum": 5,
              "title": "Max Host Magnitude",
              "type": "number"
            },
            "min_depth_percent": {
              "default": 0.5,
              "description": "Shallowest transit worth trying (1% = about 11 mmag); 0.5% suits most amateur setups",
              "maximum": 5,
              "minimum": 0.05,
              "title": "Min Depth Percent",
              "type": "number"
            },
            "min_altitude": {
              "default": 30.0,
              "description": "Minimum useful altitude in degrees",
              "maximum": 80,
              "minimum": 0,
              "title": "Min Altitude",
              "type": "number"
            },
            "full_transits_only": {
              "default": true,
              "description": "Only transits whose ingress and egress both fall in the dark window",
              "title": "Full Transits Only",
              "type": "boolean"
            },
            "max_timing_uncertainty_min": {
              "default": 30,
              "description": "Skip planets whose predicted time is less certain than this",
              "exclusiveMinimum": 0,
              "maximum": 600,
              "title": "Max Timing Uncertainty Min",
              "type": "number"
            },
            "date": {
              "anyOf": [
                {
                  "type": "string"
                },
                {
                  "type": "null"
                }
              ],
              "default": null,
              "description": "Local date (YYYY-MM-DD) whose evening starts the night. Omit for tonight.",
              "title": "Date"
            },
            "latitude": {
              "anyOf": [
                {
                  "maximum": 90,
                  "minimum": -90,
                  "type": "number"
                },
                {
                  "type": "null"
                }
              ],
              "default": null,
              "description": "Observer latitude in degrees (north positive). Omit to use place or the saved default.",
              "title": "Latitude"
            },
            "longitude": {
              "anyOf": [
                {
                  "maximum": 180,
                  "minimum": -180,
                  "type": "number"
                },
                {
                  "type": "null"
                }
              ],
              "default": null,
              "description": "Observer longitude in degrees (east positive). Omit to use place or the saved default.",
              "title": "Longitude"
            },
            "place": {
              "anyOf": [
                {
                  "type": "string"
                },
                {
                  "type": "null"
                }
              ],
              "default": null,
              "description": "Place name to observe from instead of coordinates, e.g. 'Moab, Utah'.",
              "title": "Place"
            },
            "limit": {
              "default": 20,
              "description": "Maximum transits",
              "maximum": 50,
              "minimum": 1,
              "title": "Limit",
              "type": "integer"
            }
          },
          "type": "object",
          "title": "get_transits_tonightArguments"
        },
        "name": "get_transits_tonight",
        "outputSchema": {
          "type": "object",
          "additionalProperties": true,
          "title": "get_transits_tonightDictOutput"
        }
      },
      {
        "annotations": {
          "idempotentHint": true,
          "openWorldHint": true,
          "readOnlyHint": true
        },
        "description": "Gravitational-wave detections: recent public alerts, or confirmed events from the catalog.\n\nUse for 'any recent gravitational wave detections', 'tell me about GW170817' or 'the most\nmassive black hole merger detected'. Alerts give time, false-alarm rate, detectors and the\nsource classification (binary black hole, neutron stars, noise); catalog events give masses,\nfinal mass, distance and signal-to-noise with uncertainties.\n",
        "inputSchema": {
          "properties": {
            "event": {
              "anyOf": [
                {
                  "type": "string"
                },
                {
                  "type": "null"
                }
              ],
              "default": null,
              "description": "An event: a catalog name ('GW150914', 'GW170817') or a public alert id ('S251117dq')",
              "title": "Event"
            },
            "source": {
              "default": "alerts",
              "description": "'alerts': latest significant public alerts (GraceDB); 'catalog': confirmed events with masses and distances (GWOSC)",
              "enum": [
                "alerts",
                "catalog"
              ],
              "title": "Source",
              "type": "string"
            },
            "sort_by": {
              "default": "date",
              "description": "Catalog order: newest, farthest, most massive, or loudest",
              "enum": [
                "date",
                "distance",
                "mass",
                "snr"
              ],
              "title": "Sort By",
              "type": "string"
            },
            "limit": {
              "default": 10,
              "description": "Maximum events",
              "maximum": 50,
              "minimum": 1,
              "title": "Limit",
              "type": "integer"
            },
            "include_retracted": {
              "default": false,
              "description": "Alerts: also list alerts later retracted",
              "title": "Include Retracted",
              "type": "boolean"
            },
            "min_probability": {
              "default": 0.5,
              "description": "Catalog: lowest probability of being astrophysical",
              "maximum": 1,
              "minimum": 0,
              "title": "Min Probability",
              "type": "number"
            }
          },
          "type": "object",
          "title": "get_gravitational_wave_eventsArguments"
        },
        "name": "get_gravitational_wave_events",
        "outputSchema": {
          "type": "object",
          "additionalProperties": true,
          "title": "get_gravitational_wave_eventsDictOutput"
        }
      },
      {
        "annotations": {
          "idempotentHint": true,
          "openWorldHint": true,
          "readOnlyHint": true
        },
        "description": "Field of view and image scale for a camera on a telescope or lens, and/or an eyepiece's view.\n\nUse for 'what field does my ASI2600 give on an 80 mm f/6', 'am I oversampled' or 'what\nmagnification and true field does a 25 mm eyepiece give'. Camera: field in arcminutes and\ndegrees, arcseconds per pixel and how that matches the seeing. Eyepiece: magnification, true\nfield and exit pupil.\n",
        "inputSchema": {
          "properties": {
            "focal_length_mm": {
              "description": "Focal length in mm (telescope or lens), before any Barlow or reducer",
              "exclusiveMinimum": 0,
              "maximum": 20000,
              "title": "Focal Length Mm",
              "type": "number"
            },
            "aperture_mm": {
              "anyOf": [
                {
                  "exclusiveMinimum": 0,
                  "maximum": 2000,
                  "type": "number"
                },
                {
                  "type": "null"
                }
              ],
              "default": null,
              "description": "Aperture in mm, for focal ratio, exit pupil and resolution",
              "title": "Aperture Mm"
            },
            "sensor": {
              "anyOf": [
                {
                  "type": "string"
                },
                {
                  "type": "null"
                }
              ],
              "default": null,
              "description": "Sensor preset: full_frame, aps_c_canon, aps_c, micro_four_thirds, asi6200, asi2600, asi533, asi294, asi183, asi585, asi462, asi120",
              "title": "Sensor"
            },
            "sensor_width_mm": {
              "anyOf": [
                {
                  "exclusiveMinimum": 0,
                  "maximum": 100,
                  "type": "number"
                },
                {
                  "type": "null"
                }
              ],
              "default": null,
              "description": "Sensor width in mm, if not using a preset",
              "title": "Sensor Width Mm"
            },
            "sensor_height_mm": {
              "anyOf": [
                {
                  "exclusiveMinimum": 0,
                  "maximum": 100,
                  "type": "number"
                },
                {
                  "type": "null"
                }
              ],
              "default": null,
              "description": "Sensor height in mm, if not using a preset",
              "title": "Sensor Height Mm"
            },
            "pixel_um": {
              "anyOf": [
                {
                  "exclusiveMinimum": 0,
                  "maximum": 30,
                  "type": "number"
                },
                {
                  "type": "null"
                }
              ],
              "default": null,
              "description": "Pixel size in micrometres",
              "title": "Pixel Um"
            },
            "megapixels": {
              "anyOf": [
                {
                  "exclusiveMinimum": 0,
                  "maximum": 200,
                  "type": "number"
                },
                {
                  "type": "null"
                }
              ],
              "default": null,
              "description": "Sensor megapixels, to work out pixel size",
              "title": "Megapixels"
            },
            "multiplier": {
              "default": 1.0,
              "description": "Barlow (e.g. 2) or reducer (e.g. 0.8) factor",
              "exclusiveMinimum": 0.2,
              "maximum": 6,
              "title": "Multiplier",
              "type": "number"
            },
            "seeing_arcsec": {
              "default": 2.0,
              "description": "Typical seeing (star blur) in arcseconds: 1 excellent, 2 average, 3-4 poor",
              "maximum": 6,
              "minimum": 0.3,
              "title": "Seeing Arcsec",
              "type": "number"
            },
            "eyepiece_mm": {
              "anyOf": [
                {
                  "exclusiveMinimum": 0,
                  "maximum": 100,
                  "type": "number"
                },
                {
                  "type": "null"
                }
              ],
              "default": null,
              "description": "Eyepiece focal length in mm, for the visual view",
              "title": "Eyepiece Mm"
            },
            "eyepiece_afov_deg": {
              "anyOf": [
                {
                  "exclusiveMinimum": 20,
                  "maximum": 120,
                  "type": "number"
                },
                {
                  "type": "null"
                }
              ],
              "default": null,
              "description": "Eyepiece apparent field in degrees (52 for a Plössl if omitted)",
              "title": "Eyepiece Afov Deg"
            }
          },
          "required": [
            "focal_length_mm"
          ],
          "type": "object",
          "title": "calculate_field_of_viewArguments"
        },
        "name": "calculate_field_of_view",
        "outputSchema": {
          "type": "object",
          "additionalProperties": true,
          "title": "calculate_field_of_viewDictOutput"
        }
      },
      {
        "annotations": {
          "idempotentHint": true,
          "openWorldHint": true,
          "readOnlyHint": true
        },
        "description": "Whether a target fits a camera's field, how much it fills, and which way to rotate the camera.\n\nUse for 'will M31 fit with my 400 mm and APS-C camera' or 'what focal length for the Moon'.\nUses catalogued sizes and orientations (OpenNGC) or a planet's current apparent size, and\nsuggests a focal length or a mosaic when the fit is poor.\n",
        "inputSchema": {
          "properties": {
            "target": {
              "description": "Object to frame: 'M31', 'North America Nebula', 'Moon', 'Jupiter'",
              "title": "Target",
              "type": "string"
            },
            "focal_length_mm": {
              "description": "Focal length in mm (telescope or lens), before any Barlow or reducer",
              "exclusiveMinimum": 0,
              "maximum": 20000,
              "title": "Focal Length Mm",
              "type": "number"
            },
            "sensor": {
              "anyOf": [
                {
                  "type": "string"
                },
                {
                  "type": "null"
                }
              ],
              "default": null,
              "description": "Sensor preset: full_frame, aps_c_canon, aps_c, micro_four_thirds, asi6200, asi2600, asi533, asi294, asi183, asi585, asi462, asi120",
              "title": "Sensor"
            },
            "sensor_width_mm": {
              "anyOf": [
                {
                  "exclusiveMinimum": 0,
                  "maximum": 100,
                  "type": "number"
                },
                {
                  "type": "null"
                }
              ],
              "default": null,
              "description": "Sensor width in mm, if not using a preset",
              "title": "Sensor Width Mm"
            },
            "sensor_height_mm": {
              "anyOf": [
                {
                  "exclusiveMinimum": 0,
                  "maximum": 100,
                  "type": "number"
                },
                {
                  "type": "null"
                }
              ],
              "default": null,
              "description": "Sensor height in mm, if not using a preset",
              "title": "Sensor Height Mm"
            },
            "multiplier": {
              "default": 1.0,
              "description": "Barlow (e.g. 2) or reducer (e.g. 0.8) factor",
              "exclusiveMinimum": 0.2,
              "maximum": 6,
              "title": "Multiplier",
              "type": "number"
            }
          },
          "required": [
            "target",
            "focal_length_mm"
          ],
          "type": "object",
          "title": "frame_targetArguments"
        },
        "name": "frame_target",
        "outputSchema": {
          "type": "object",
          "additionalProperties": true,
          "title": "frame_targetDictOutput"
        }
      },
      {
        "annotations": {
          "idempotentHint": true,
          "openWorldHint": true,
          "readOnlyHint": true
        },
        "description": "A mosaic plan: how many panels, and the RA/Dec centre of each, to cover a large target.\n\nUse for 'how many panels to cover the Veil Nebula with my 600 mm' or to get panel\ncoordinates for a sequencer. Lays a grid of camera fields with the requested overlap,\nrotated along the target's long axis.\n",
        "inputSchema": {
          "properties": {
            "focal_length_mm": {
              "description": "Focal length in mm (telescope or lens), before any Barlow or reducer",
              "exclusiveMinimum": 0,
              "maximum": 20000,
              "title": "Focal Length Mm",
              "type": "number"
            },
            "target": {
              "anyOf": [
                {
                  "type": "string"
                },
                {
                  "type": "null"
                }
              ],
              "default": null,
              "description": "Object to cover; or give ra_deg, dec_deg, width_arcmin and height_arcmin",
              "title": "Target"
            },
            "ra_deg": {
              "anyOf": [
                {
                  "exclusiveMaximum": 360,
                  "minimum": 0,
                  "type": "number"
                },
                {
                  "type": "null"
                }
              ],
              "default": null,
              "description": "Centre right ascension (J2000 degrees)",
              "title": "Ra Deg"
            },
            "dec_deg": {
              "anyOf": [
                {
                  "maximum": 90,
                  "minimum": -90,
                  "type": "number"
                },
                {
                  "type": "null"
                }
              ],
              "default": null,
              "description": "Centre declination (J2000 degrees)",
              "title": "Dec Deg"
            },
            "width_arcmin": {
              "anyOf": [
                {
                  "exclusiveMinimum": 0,
                  "maximum": 3600,
                  "type": "number"
                },
                {
                  "type": "null"
                }
              ],
              "default": null,
              "description": "Area to cover, along the width axis",
              "title": "Width Arcmin"
            },
            "height_arcmin": {
              "anyOf": [
                {
                  "exclusiveMinimum": 0,
                  "maximum": 3600,
                  "type": "number"
                },
                {
                  "type": "null"
                }
              ],
              "default": null,
              "description": "Area to cover, across the width axis",
              "title": "Height Arcmin"
            },
            "angle_deg": {
              "anyOf": [
                {
                  "exclusiveMaximum": 360,
                  "minimum": 0,
                  "type": "number"
                },
                {
                  "type": "null"
                }
              ],
              "default": null,
              "description": "Position angle of the mosaic's width axis, east of north; defaults to the target's major axis, else 90 (east-west)",
              "title": "Angle Deg"
            },
            "overlap_percent": {
              "default": 15,
              "description": "Overlap between neighbouring panels",
              "maximum": 50,
              "minimum": 0,
              "title": "Overlap Percent",
              "type": "number"
            },
            "sensor": {
              "anyOf": [
                {
                  "type": "string"
                },
                {
                  "type": "null"
                }
              ],
              "default": null,
              "description": "Sensor preset: full_frame, aps_c_canon, aps_c, micro_four_thirds, asi6200, asi2600, asi533, asi294, asi183, asi585, asi462, asi120",
              "title": "Sensor"
            },
            "sensor_width_mm": {
              "anyOf": [
                {
                  "exclusiveMinimum": 0,
                  "maximum": 100,
                  "type": "number"
                },
                {
                  "type": "null"
                }
              ],
              "default": null,
              "description": "Sensor width in mm, if not using a preset",
              "title": "Sensor Width Mm"
            },
            "sensor_height_mm": {
              "anyOf": [
                {
                  "exclusiveMinimum": 0,
                  "maximum": 100,
                  "type": "number"
                },
                {
                  "type": "null"
                }
              ],
              "default": null,
              "description": "Sensor height in mm, if not using a preset",
              "title": "Sensor Height Mm"
            },
            "multiplier": {
              "default": 1.0,
              "description": "Barlow (e.g. 2) or reducer (e.g. 0.8) factor",
              "exclusiveMinimum": 0.2,
              "maximum": 6,
              "title": "Multiplier",
              "type": "number"
            }
          },
          "required": [
            "focal_length_mm"
          ],
          "type": "object",
          "title": "plan_mosaicArguments"
        },
        "name": "plan_mosaic",
        "outputSchema": {
          "type": "object",
          "additionalProperties": true,
          "title": "plan_mosaicDictOutput"
        }
      },
      {
        "annotations": {
          "idempotentHint": true,
          "openWorldHint": true,
          "readOnlyHint": true
        },
        "description": "Longest untracked exposure before stars trail, by the NPF rule (and the older 500 rule).\n\nUse for 'how long can I expose the Milky Way at 14 mm f/2.8 on my camera'. Needs the pixel\nsize (directly, from a sensor preset, or from sensor size and megapixels). Aiming away from\nthe celestial equator allows longer exposures; give a target or declination to include that.\n",
        "inputSchema": {
          "properties": {
            "focal_length_mm": {
              "description": "Lens focal length in mm (actual, not 35 mm equivalent)",
              "exclusiveMinimum": 0,
              "maximum": 2000,
              "title": "Focal Length Mm",
              "type": "number"
            },
            "f_number": {
              "description": "Aperture as an f-number, e.g. 2.8",
              "exclusiveMinimum": 0.7,
              "maximum": 32,
              "title": "F Number",
              "type": "number"
            },
            "sensor": {
              "anyOf": [
                {
                  "type": "string"
                },
                {
                  "type": "null"
                }
              ],
              "default": null,
              "description": "Sensor preset: full_frame, aps_c_canon, aps_c, micro_four_thirds, asi6200, asi2600, asi533, asi294, asi183, asi585, asi462, asi120",
              "title": "Sensor"
            },
            "sensor_width_mm": {
              "anyOf": [
                {
                  "exclusiveMinimum": 0,
                  "maximum": 100,
                  "type": "number"
                },
                {
                  "type": "null"
                }
              ],
              "default": null,
              "description": "Sensor width in mm, if not using a preset",
              "title": "Sensor Width Mm"
            },
            "sensor_height_mm": {
              "anyOf": [
                {
                  "exclusiveMinimum": 0,
                  "maximum": 100,
                  "type": "number"
                },
                {
                  "type": "null"
                }
              ],
              "default": null,
              "description": "Sensor height in mm, if not using a preset",
              "title": "Sensor Height Mm"
            },
            "pixel_um": {
              "anyOf": [
                {
                  "exclusiveMinimum": 0,
                  "maximum": 30,
                  "type": "number"
                },
                {
                  "type": "null"
                }
              ],
              "default": null,
              "description": "Pixel size in micrometres",
              "title": "Pixel Um"
            },
            "megapixels": {
              "anyOf": [
                {
                  "exclusiveMinimum": 0,
                  "maximum": 200,
                  "type": "number"
                },
                {
                  "type": "null"
                }
              ],
              "default": null,
              "description": "Sensor megapixels, to work out pixel size",
              "title": "Megapixels"
            },
            "crop_factor": {
              "anyOf": [
                {
                  "exclusiveMinimum": 0.3,
                  "maximum": 10,
                  "type": "number"
                },
                {
                  "type": "null"
                }
              ],
              "default": null,
              "description": "Crop factor for the 500 rule; worked out from the sensor if omitted",
              "title": "Crop Factor"
            },
            "target": {
              "anyOf": [
                {
                  "type": "string"
                },
                {
                  "type": "null"
                }
              ],
              "default": null,
              "description": "Aim point, for its declination: 'Milky Way core', 'Polaris', 'M31'",
              "title": "Target"
            },
            "declination_deg": {
              "anyOf": [
                {
                  "maximum": 90,
                  "minimum": -90,
                  "type": "number"
                },
                {
                  "type": "null"
                }
              ],
              "default": null,
              "description": "Declination of the aim point, instead of a target",
              "title": "Declination Deg"
            }
          },
          "required": [
            "focal_length_mm",
            "f_number"
          ],
          "type": "object",
          "title": "calculate_exposureArguments"
        },
        "name": "calculate_exposure",
        "outputSchema": {
          "type": "object",
          "additionalProperties": true,
          "title": "calculate_exposureDictOutput"
        }
      },
      {
        "annotations": {
          "idempotentHint": true,
          "openWorldHint": true,
          "readOnlyHint": true
        },
        "description": "When and where to photograph the Milky Way's core: dark, moonless windows with the galactic centre up.\n\nUse for 'can I shoot the Milky Way core tonight', 'best nights this month for Milky Way photos'\nor 'when does Milky Way season start here'. Gives the shooting window, the core's altitude and\ncompass direction at its start, best moment and end, how steeply the band is tilted (portrait\nframe or panorama), the Moon, and the season month by month. Does not check clouds (use\nget_sky_forecast); for exposure length use calculate_exposure with target 'Milky Way core'.\n",
        "inputSchema": {
          "properties": {
            "date": {
              "anyOf": [
                {
                  "type": "string"
                },
                {
                  "type": "null"
                }
              ],
              "default": null,
              "description": "Local date (YYYY-MM-DD) whose evening starts the night. Omit for tonight.",
              "title": "Date"
            },
            "days": {
              "default": 1,
              "description": "Nights to plan, starting with date; more than one ranks them",
              "maximum": 60,
              "minimum": 1,
              "title": "Days",
              "type": "integer"
            },
            "min_altitude": {
              "default": 10.0,
              "description": "Lowest useful altitude of the core in degrees",
              "maximum": 60,
              "minimum": 0,
              "title": "Min Altitude",
              "type": "number"
            },
            "terrain": {
              "default": true,
              "description": "Account for hills and mountains on the local horizon (first use per location takes a few seconds)",
              "title": "Terrain",
              "type": "boolean"
            },
            "latitude": {
              "anyOf": [
                {
                  "maximum": 90,
                  "minimum": -90,
                  "type": "number"
                },
                {
                  "type": "null"
                }
              ],
              "default": null,
              "description": "Observer latitude in degrees (north positive). Omit to use place or the saved default.",
              "title": "Latitude"
            },
            "longitude": {
              "anyOf": [
                {
                  "maximum": 180,
                  "minimum": -180,
                  "type": "number"
                },
                {
                  "type": "null"
                }
              ],
              "default": null,
              "description": "Observer longitude in degrees (east positive). Omit to use place or the saved default.",
              "title": "Longitude"
            },
            "place": {
              "anyOf": [
                {
                  "type": "string"
                },
                {
                  "type": "null"
                }
              ],
              "default": null,
              "description": "Place name to observe from instead of coordinates, e.g. 'Moab, Utah'.",
              "title": "Place"
            }
          },
          "type": "object",
          "title": "plan_milky_way_shotArguments"
        },
        "name": "plan_milky_way_shot",
        "outputSchema": {
          "type": "object",
          "additionalProperties": true,
          "title": "plan_milky_way_shotDictOutput"
        }
      },
      {
        "annotations": {
          "idempotentHint": true,
          "openWorldHint": true,
          "readOnlyHint": true
        },
        "description": "A survey image of any patch of sky, from DSS, Pan-STARRS, SDSS, Legacy Surveys, 2MASS, WISE and others.\n\nUse for 'show me what M51 looks like', 'get a DSS image of these coordinates' or a reference\nframe to compare with your own photo (spotting a new star, checking framing). North up, east\nleft. The image is shown and saved under ~/.astronomy-mcp/images.\n",
        "inputSchema": {
          "properties": {
            "target": {
              "anyOf": [
                {
                  "type": "string"
                },
                {
                  "type": "null"
                }
              ],
              "default": null,
              "description": "Object to centre on: 'M51', 'Stephan's Quintet', 'Uranus'; or give ra_deg and dec_deg",
              "title": "Target"
            },
            "ra_deg": {
              "anyOf": [
                {
                  "exclusiveMaximum": 360,
                  "minimum": 0,
                  "type": "number"
                },
                {
                  "type": "null"
                }
              ],
              "default": null,
              "description": "Centre right ascension (J2000 degrees), instead of a target",
              "title": "Ra Deg"
            },
            "dec_deg": {
              "anyOf": [
                {
                  "maximum": 90,
                  "minimum": -90,
                  "type": "number"
                },
                {
                  "type": "null"
                }
              ],
              "default": null,
              "description": "Centre declination (J2000 degrees), instead of a target",
              "title": "Dec Deg"
            },
            "fov_deg": {
              "anyOf": [
                {
                  "exclusiveMinimum": 0.005,
                  "maximum": 30,
                  "type": "number"
                },
                {
                  "type": "null"
                }
              ],
              "default": null,
              "description": "Width of the field in degrees. Defaults to 1.5x the target's catalogued size, else 0.5",
              "title": "Fov Deg"
            },
            "survey": {
              "default": "auto",
              "description": "Image source. 'auto': DSS2 (whole sky) up to 5°, the Mellinger photographic mosaic for wider fields. Pan-STARRS is sharper but only north of -30°; 2MASS and WISE are infrared.",
              "enum": [
                "auto",
                "dss2_color",
                "dss2_red",
                "dss2_blue",
                "panstarrs_color",
                "panstarrs_g",
                "panstarrs_r",
                "sdss_color",
                "legacy_color",
                "2mass_color",
                "wise_color",
                "mellinger_color"
              ],
              "title": "Survey",
              "type": "string"
            },
            "width_px": {
              "default": 800,
              "description": "Image width in pixels",
              "maximum": 3000,
              "minimum": 64,
              "title": "Width Px",
              "type": "integer"
            },
            "height_px": {
              "anyOf": [
                {
                  "maximum": 3000,
                  "minimum": 64,
                  "type": "integer"
                },
                {
                  "type": "null"
                }
              ],
              "default": null,
              "description": "Image height in pixels; defaults to width_px",
              "title": "Height Px"
            },
            "image_format": {
              "default": "jpg",
              "description": "'fits' keeps the data and a WCS header; it is saved, not shown",
              "enum": [
                "jpg",
                "png",
                "fits"
              ],
              "title": "Image Format",
              "type": "string"
            },
            "time": {
              "anyOf": [
                {
                  "type": "string"
                },
                {
                  "type": "null"
                }
              ],
              "default": null,
              "description": "For a planet: ISO 8601 time to place it at (naive = the saved location's local time). Omit for now.",
              "title": "Time"
            }
          },
          "type": "object",
          "title": "get_survey_cutoutArguments"
        },
        "name": "get_survey_cutout"
      },
      {
        "annotations": {
          "idempotentHint": true,
          "openWorldHint": true,
          "readOnlyHint": true
        },
        "description": "A finder chart: a survey image with the target marked, your camera frame or eyepiece field, Telrad rings,\nnearby objects labelled, compass and scale bar, flipped to match what your telescope shows.\n\nUse for 'make me a finder chart for M97', 'how do I find NGC 891 with my Telrad', 'show my\ncamera's framing on M31' or 'where is Neptune among the stars'. Shown and saved as a PNG under\n~/.astronomy-mcp/charts for printing.\n",
        "inputSchema": {
          "properties": {
            "target": {
              "anyOf": [
                {
                  "type": "string"
                },
                {
                  "type": "null"
                }
              ],
              "default": null,
              "description": "Object to find: 'M97', 'NGC 891', 'Neptune'; or give ra_deg and dec_deg",
              "title": "Target"
            },
            "ra_deg": {
              "anyOf": [
                {
                  "exclusiveMaximum": 360,
                  "minimum": 0,
                  "type": "number"
                },
                {
                  "type": "null"
                }
              ],
              "default": null,
              "description": "Centre right ascension (J2000 degrees), instead of a target",
              "title": "Ra Deg"
            },
            "dec_deg": {
              "anyOf": [
                {
                  "maximum": 90,
                  "minimum": -90,
                  "type": "number"
                },
                {
                  "type": "null"
                }
              ],
              "default": null,
              "description": "Centre declination (J2000 degrees), instead of a target",
              "title": "Dec Deg"
            },
            "fov_deg": {
              "anyOf": [
                {
                  "maximum": 30,
                  "minimum": 0.05,
                  "type": "number"
                },
                {
                  "type": "null"
                }
              ],
              "default": null,
              "description": "Chart width in degrees. Defaults to twice the camera frame, 2.5x the eyepiece field, 9° with Telrad rings, else from the target's size",
              "title": "Fov Deg"
            },
            "focal_length_mm": {
              "anyOf": [
                {
                  "exclusiveMinimum": 0,
                  "maximum": 20000,
                  "type": "number"
                },
                {
                  "type": "null"
                }
              ],
              "default": null,
              "description": "Telescope or lens focal length, to draw the camera frame and/or eyepiece field",
              "title": "Focal Length Mm"
            },
            "sensor": {
              "anyOf": [
                {
                  "type": "string"
                },
                {
                  "type": "null"
                }
              ],
              "default": null,
              "description": "Sensor preset: full_frame, aps_c_canon, aps_c, micro_four_thirds, asi6200, asi2600, asi533, asi294, asi183, asi585, asi462, asi120",
              "title": "Sensor"
            },
            "sensor_width_mm": {
              "anyOf": [
                {
                  "exclusiveMinimum": 0,
                  "maximum": 100,
                  "type": "number"
                },
                {
                  "type": "null"
                }
              ],
              "default": null,
              "description": "Sensor width in mm, if not using a preset",
              "title": "Sensor Width Mm"
            },
            "sensor_height_mm": {
              "anyOf": [
                {
                  "exclusiveMinimum": 0,
                  "maximum": 100,
                  "type": "number"
                },
                {
                  "type": "null"
                }
              ],
              "default": null,
              "description": "Sensor height in mm, if not using a preset",
              "title": "Sensor Height Mm"
            },
            "rotation_deg": {
              "anyOf": [
                {
                  "exclusiveMaximum": 360,
                  "minimum": 0,
                  "type": "number"
                },
                {
                  "type": "null"
                }
              ],
              "default": null,
              "description": "Camera angle: position angle of the sensor's long side, east of north. Defaults to the target's long axis, else 90 (east-west)",
              "title": "Rotation Deg"
            },
            "eyepiece_mm": {
              "anyOf": [
                {
                  "exclusiveMinimum": 0,
                  "maximum": 100,
                  "type": "number"
                },
                {
                  "type": "null"
                }
              ],
              "default": null,
              "description": "Eyepiece focal length in mm, to draw its true field",
              "title": "Eyepiece Mm"
            },
            "eyepiece_afov_deg": {
              "anyOf": [
                {
                  "exclusiveMinimum": 20,
                  "maximum": 120,
                  "type": "number"
                },
                {
                  "type": "null"
                }
              ],
              "default": null,
              "description": "Eyepiece apparent field in degrees (52 if omitted)",
              "title": "Eyepiece Afov Deg"
            },
            "multiplier": {
              "default": 1.0,
              "description": "Barlow (e.g. 2) or reducer (e.g. 0.8) factor",
              "exclusiveMinimum": 0.2,
              "maximum": 6,
              "title": "Multiplier",
              "type": "number"
            },
            "telrad": {
              "default": false,
              "description": "Draw Telrad rings (0.5°, 2° and 4°) around the target",
              "title": "Telrad",
              "type": "boolean"
            },
            "orientation": {
              "default": "north_up",
              "description": "'north_up' for naked eye, binoculars and correct-image finders; 'mirrored' for a star diagonal; 'rotated' (180°) for a Newtonian or straight-through finder",
              "enum": [
                "north_up",
                "mirrored",
                "rotated"
              ],
              "title": "Orientation",
              "type": "string"
            },
            "style": {
              "default": "print",
              "description": "'print': black stars on white; 'photo': the survey image as it is",
              "enum": [
                "print",
                "photo"
              ],
              "title": "Style",
              "type": "string"
            },
            "survey": {
              "default": "auto",
              "description": "Image source. 'auto': DSS2 (whole sky) up to 5°, the Mellinger photographic mosaic for wider fields. Pan-STARRS is sharper but only north of -30°; 2MASS and WISE are infrared.",
              "enum": [
                "auto",
                "dss2_color",
                "dss2_red",
                "dss2_blue",
                "panstarrs_color",
                "panstarrs_g",
                "panstarrs_r",
                "sdss_color",
                "legacy_color",
                "2mass_color",
                "wise_color",
                "mellinger_color"
              ],
              "title": "Survey",
              "type": "string"
            },
            "label_objects": {
              "default": true,
              "description": "Mark and name other NGC/IC/Messier objects in the field",
              "title": "Label Objects",
              "type": "boolean"
            },
            "size_px": {
              "default": 900,
              "description": "Chart width in pixels",
              "maximum": 2000,
              "minimum": 400,
              "title": "Size Px",
              "type": "integer"
            },
            "time": {
              "anyOf": [
                {
                  "type": "string"
                },
                {
                  "type": "null"
                }
              ],
              "default": null,
              "description": "For a planet: ISO 8601 time to place it at (naive = the saved location's local time). Omit for now.",
              "title": "Time"
            }
          },
          "type": "object",
          "title": "generate_finder_chartArguments"
        },
        "name": "generate_finder_chart"
      },
      {
        "annotations": {
          "destructiveHint": false,
          "idempotentHint": false,
          "openWorldHint": true,
          "readOnlyHint": false
        },
        "description": "Plate-solve an astrophoto with Astrometry.net: exact centre, field size, pixel scale, camera angle and named objects.\n\nUse for 'what is in this photo', 'where was my camera pointed' or 'what are my image scale\nand camera rotation'. Uploads the image to nova.astrometry.net (marked private) and needs a\nfree API key in the ASTROMETRY_NET_API_KEY environment variable. Solving takes one to several\nminutes; if it isn't done within wait_seconds, call again with the returned submission_id.\nFocal length and sensor, or a rough target, speed it up. Export camera raw files to JPEG,\nTIFF or FITS first.\n",
        "inputSchema": {
          "properties": {
            "image": {
              "anyOf": [
                {
                  "type": "string"
                },
                {
                  "type": "null"
                }
              ],
              "default": null,
              "description": "Local path to a JPEG, PNG, TIFF or FITS file, or an http(s) URL of one",
              "title": "Image"
            },
            "submission_id": {
              "anyOf": [
                {
                  "minimum": 1,
                  "type": "integer"
                },
                {
                  "type": "null"
                }
              ],
              "default": null,
              "description": "Check on an earlier submission instead of uploading",
              "title": "Submission Id"
            },
            "wait_seconds": {
              "default": 60,
              "description": "How long to wait for the solve before handing back the submission id",
              "maximum": 600,
              "minimum": 0,
              "title": "Wait Seconds",
              "type": "integer"
            },
            "target": {
              "anyOf": [
                {
                  "type": "string"
                },
                {
                  "type": "null"
                }
              ],
              "default": null,
              "description": "Roughly where the image points, to speed up the solve: 'M31', 'Vega'",
              "title": "Target"
            },
            "ra_deg": {
              "anyOf": [
                {
                  "exclusiveMaximum": 360,
                  "minimum": 0,
                  "type": "number"
                },
                {
                  "type": "null"
                }
              ],
              "default": null,
              "description": "Approximate centre RA (J2000 degrees), instead of a target",
              "title": "Ra Deg"
            },
            "dec_deg": {
              "anyOf": [
                {
                  "maximum": 90,
                  "minimum": -90,
                  "type": "number"
                },
                {
                  "type": "null"
                }
              ],
              "default": null,
              "description": "Approximate centre declination (J2000 degrees)",
              "title": "Dec Deg"
            },
            "search_radius_deg": {
              "default": 10.0,
              "description": "How far from the target or RA/Dec to search",
              "exclusiveMinimum": 0,
              "maximum": 180,
              "title": "Search Radius Deg",
              "type": "number"
            },
            "arcsec_per_pixel": {
              "anyOf": [
                {
                  "exclusiveMinimum": 0.01,
                  "maximum": 3600,
                  "type": "number"
                },
                {
                  "type": "null"
                }
              ],
              "default": null,
              "description": "Image scale, if known",
              "title": "Arcsec Per Pixel"
            },
            "focal_length_mm": {
              "anyOf": [
                {
                  "exclusiveMinimum": 0,
                  "maximum": 20000,
                  "type": "number"
                },
                {
                  "type": "null"
                }
              ],
              "default": null,
              "description": "Focal length used, including any reducer or Barlow, for a scale hint",
              "title": "Focal Length Mm"
            },
            "sensor": {
              "anyOf": [
                {
                  "type": "string"
                },
                {
                  "type": "null"
                }
              ],
              "default": null,
              "description": "Sensor preset: full_frame, aps_c_canon, aps_c, micro_four_thirds, asi6200, asi2600, asi533, asi294, asi183, asi585, asi462, asi120",
              "title": "Sensor"
            },
            "sensor_width_mm": {
              "anyOf": [
                {
                  "exclusiveMinimum": 0,
                  "maximum": 100,
                  "type": "number"
                },
                {
                  "type": "null"
                }
              ],
              "default": null,
              "description": "Sensor width in mm, if not using a preset",
              "title": "Sensor Width Mm"
            },
            "sensor_height_mm": {
              "anyOf": [
                {
                  "exclusiveMinimum": 0,
                  "maximum": 100,
                  "type": "number"
                },
                {
                  "type": "null"
                }
              ],
              "default": null,
              "description": "Sensor height in mm, if not using a preset",
              "title": "Sensor Height Mm"
            },
            "pixel_um": {
              "anyOf": [
                {
                  "exclusiveMinimum": 0,
                  "maximum": 30,
                  "type": "number"
                },
                {
                  "type": "null"
                }
              ],
              "default": null,
              "description": "Pixel size in micrometres",
              "title": "Pixel Um"
            }
          },
          "type": "object",
          "title": "plate_solve_imageArguments"
        },
        "name": "plate_solve_image",
        "outputSchema": {
          "type": "object",
          "additionalProperties": true,
          "title": "plate_solve_imageDictOutput"
        }
      },
      {
        "annotations": {
          "idempotentHint": true,
          "openWorldHint": true,
          "readOnlyHint": true
        },
        "description": "Aurora chances and geomagnetic storm levels, now and for the next 3 days (NOAA SWPC).\n\nUse for 'will I see the northern lights', 'is there a geomagnetic storm' or 'what's the Kp'.\nWith a location, adds the current aurora probability overhead and toward the pole.\n",
        "inputSchema": {
          "properties": {
            "latitude": {
              "anyOf": [
                {
                  "maximum": 90,
                  "minimum": -90,
                  "type": "number"
                },
                {
                  "type": "null"
                }
              ],
              "default": null,
              "description": "Observer latitude in degrees (north positive). Omit to use place or the saved default.",
              "title": "Latitude"
            },
            "longitude": {
              "anyOf": [
                {
                  "maximum": 180,
                  "minimum": -180,
                  "type": "number"
                },
                {
                  "type": "null"
                }
              ],
              "default": null,
              "description": "Observer longitude in degrees (east positive). Omit to use place or the saved default.",
              "title": "Longitude"
            },
            "place": {
              "anyOf": [
                {
                  "type": "string"
                },
                {
                  "type": "null"
                }
              ],
              "default": null,
              "description": "Place name to observe from instead of coordinates, e.g. 'Moab, Utah'.",
              "title": "Place"
            }
          },
          "type": "object",
          "title": "get_space_weatherArguments"
        },
        "name": "get_space_weather",
        "outputSchema": {
          "type": "object",
          "additionalProperties": true,
          "title": "get_space_weatherDictOutput"
        }
      },
      {
        "annotations": {
          "idempotentHint": true,
          "openWorldHint": true,
          "readOnlyHint": true
        },
        "description": "Upcoming rocket launches worldwide with times, rockets, missions, pads and webcasts.\n\nUse for 'when is the next SpaceX/Starship launch' or 'any launches I could see from here'\n(max_distance_km filters to nearby pads). Schedules change often, so prefer this over memory.\n",
        "inputSchema": {
          "properties": {
            "limit": {
              "default": 10,
              "description": "Maximum launches",
              "maximum": 25,
              "minimum": 1,
              "title": "Limit",
              "type": "integer"
            },
            "search": {
              "anyOf": [
                {
                  "type": "string"
                },
                {
                  "type": "null"
                }
              ],
              "default": null,
              "description": "Filter by rocket, provider or mission text, e.g. 'Starship', 'Rocket Lab'",
              "title": "Search"
            },
            "max_distance_km": {
              "anyOf": [
                {
                  "exclusiveMinimum": 0,
                  "type": "number"
                },
                {
                  "type": "null"
                }
              ],
              "default": null,
              "description": "Only launches from pads within this distance of the observer",
              "title": "Max Distance Km"
            },
            "latitude": {
              "anyOf": [
                {
                  "maximum": 90,
                  "minimum": -90,
                  "type": "number"
                },
                {
                  "type": "null"
                }
              ],
              "default": null,
              "description": "Observer latitude in degrees (north positive). Omit to use place or the saved default.",
              "title": "Latitude"
            },
            "longitude": {
              "anyOf": [
                {
                  "maximum": 180,
                  "minimum": -180,
                  "type": "number"
                },
                {
                  "type": "null"
                }
              ],
              "default": null,
              "description": "Observer longitude in degrees (east positive). Omit to use place or the saved default.",
              "title": "Longitude"
            },
            "place": {
              "anyOf": [
                {
                  "type": "string"
                },
                {
                  "type": "null"
                }
              ],
              "default": null,
              "description": "Place name to observe from instead of coordinates, e.g. 'Moab, Utah'.",
              "title": "Place"
            }
          },
          "type": "object",
          "title": "get_upcoming_launchesArguments"
        },
        "name": "get_upcoming_launches",
        "outputSchema": {
          "type": "object",
          "additionalProperties": true,
          "title": "get_upcoming_launchesDictOutput"
        }
      }
    ]
  }
}
```

### Response, exact bytes on the wire (123299 bytes, one line)

```json
{"jsonrpc":"2.0","id":2,"result":{"tools":[{"annotations":{"idempotentHint":true,"openWorldHint":true,"readOnlyHint":true},"description":"Turn a place name into coordinates, elevation and timezone (Open-Meteo geocoder).\n\nUseful when a place is ambiguous and the user should pick; other tools also accept a\nplace name directly.\n","inputSchema":{"properties":{"query":{"description":"Place name, optionally qualified: 'Moab, Utah', 'Cherry Springs State Park'","title":"Query","type":"string"},"count":{"default":5,"description":"Maximum candidates","maximum":10,"minimum":1,"title":"Count","type":"integer"}},"required":["query"],"type":"object","title":"geocode_locationArguments"},"name":"geocode_location","outputSchema":{"type":"object","additionalProperties":true,"title":"geocode_locationDictOutput"}},{"annotations":{"destructiveHint":false,"idempotentHint":true,"openWorldHint":true,"readOnlyHint":false},"description":"Save the observer's default location so later questions don't need it repeated.\n\nCall this when the user tells you where they usually observe from. Only pass bortle if\nthe user states it; otherwise sky darkness comes from the light-pollution atlas, which\nthis call reports. Stored in ~/.astronomy-mcp/config.json across sessions.\n","inputSchema":{"properties":{"place":{"anyOf":[{"type":"string"},{"type":"null"}],"default":null,"description":"Place name to observe from instead of coordinates, e.g. 'Moab, Utah'.","title":"Place"},"latitude":{"anyOf":[{"maximum":90,"minimum":-90,"type":"number"},{"type":"null"}],"default":null,"description":"Observer latitude in degrees (north positive). Omit to use place or the saved default.","title":"Latitude"},"longitude":{"anyOf":[{"maximum":180,"minimum":-180,"type":"number"},{"type":"null"}],"default":null,"description":"Observer longitude in degrees (east positive). Omit to use place or the saved default.","title":"Longitude"},"name":{"anyOf":[{"type":"string"},{"type":"null"}],"default":null,"description":"Friendly name to store, e.g. 'Backyard'","title":"Name"},"bortle":{"anyOf":[{"maximum":9,"minimum":1,"type":"integer"},{"type":"null"}],"default":null,"description":"Bortle class of the sky (1 pristine to 9 inner city). Omit to use the saved value or the light-pollution atlas.","title":"Bortle"}},"type":"object","title":"set_default_locationArguments"},"name":"set_default_location","outputSchema":{"type":"object","additionalProperties":true,"title":"set_default_locationDictOutput"}},{"annotations":{"idempotentHint":true,"openWorldHint":true,"readOnlyHint":true},"description":"Show the saved default observing location, if any.","inputSchema":{"properties":{},"type":"object","title":"get_default_locationArguments"},"name":"get_default_location","outputSchema":{"type":"object","additionalProperties":true,"title":"get_default_locationDictOutput"}},{"annotations":{"idempotentHint":true,"openWorldHint":true,"readOnlyHint":true},"description":"Look up a celestial object in SIMBAD by name or catalog identifier.\n\nReturns coordinates, object type, spectral/morphological type, parallax (and derived\ndistance), proper motion, radial velocity, redshift, multi-band magnitudes and aliases.\ndescribe_object is usually the better first call; use this for raw SIMBAD data.\n","inputSchema":{"properties":{"identifier":{"description":"Any SIMBAD identifier or common name, e.g. 'M31', 'Betelgeuse', 'HD 39801', 'NGC 1976'","title":"Identifier","type":"string"}},"required":["identifier"],"type":"object","title":"simbad_lookupArguments"},"name":"simbad_lookup","outputSchema":{"type":"object","additionalProperties":true,"title":"simbad_lookupDictOutput"}},{"annotations":{"idempotentHint":true,"openWorldHint":true,"readOnlyHint":true},"description":"Find SIMBAD objects within a radius of a sky position, sorted nearest first.\n\nFor questions like 'what is at these coordinates' or 'what else is near this object'.\n","inputSchema":{"properties":{"ra_deg":{"description":"Right ascension, decimal degrees (ICRS/J2000)","exclusiveMaximum":360,"minimum":0,"title":"Ra Deg","type":"number"},"dec_deg":{"description":"Declination, decimal degrees (ICRS/J2000)","maximum":90,"minimum":-90,"title":"Dec Deg","type":"number"},"radius_arcmin":{"default":5.0,"description":"Search radius in arcminutes (max 60)","exclusiveMinimum":0,"maximum":60,"title":"Radius Arcmin","type":"number"},"object_type":{"anyOf":[{"type":"string"},{"type":"null"}],"default":null,"description":"Optional SIMBAD object-type code to filter on, e.g. '*' (star), 'G' (galaxy), 'QSO', 'PN', 'OpC', 'V*' (variable star), 'EB*'","title":"Object Type"},"max_v_mag":{"anyOf":[{"type":"number"},{"type":"null"}],"default":null,"description":"Only return objects with V magnitude at or brighter than this","title":"Max V Mag"},"limit":{"default":20,"description":"Maximum number of results","maximum":200,"minimum":1,"title":"Limit","type":"integer"}},"required":["ra_deg","dec_deg"],"type":"object","title":"simbad_cone_searchArguments"},"name":"simbad_cone_search","outputSchema":{"type":"object","additionalProperties":true,"title":"simbad_cone_searchDictOutput"}},{"annotations":{"idempotentHint":true,"openWorldHint":true,"readOnlyHint":true},"description":"Look up a variable star in the AAVSO International Variable Star Index (VSX).\n\nReturns variability type, period, epoch, magnitude range, spectral type, discoverer,\nconstellation and a link to the VSX detail page. Use for periods and brightness ranges\nof variable stars rather than recalling them.\n","inputSchema":{"properties":{"name":{"description":"Variable star name, e.g. 'R Leo', 'Mira', 'SS Cyg', 'delta Cep'","title":"Name","type":"string"}},"required":["name"],"type":"object","title":"vsx_lookupArguments"},"name":"vsx_lookup","outputSchema":{"type":"object","additionalProperties":true,"title":"vsx_lookupDictOutput"}},{"annotations":{"idempotentHint":true,"openWorldHint":true,"readOnlyHint":true},"description":"Find known variable stars in VSX within a radius of a sky position, nearest first.","inputSchema":{"properties":{"ra_deg":{"description":"Right ascension, decimal degrees (ICRS/J2000)","exclusiveMaximum":360,"minimum":0,"title":"Ra Deg","type":"number"},"dec_deg":{"description":"Declination, decimal degrees (ICRS/J2000)","maximum":90,"minimum":-90,"title":"Dec Deg","type":"number"},"radius_deg":{"default":0.5,"description":"Search radius in degrees (max 5)","exclusiveMinimum":0,"maximum":5,"title":"Radius Deg","type":"number"},"max_mag":{"anyOf":[{"type":"number"},{"type":"null"}],"default":null,"description":"Only return stars reaching this magnitude or brighter at maximum","title":"Max Mag"},"limit":{"default":25,"description":"Maximum number of results","maximum":500,"minimum":1,"title":"Limit","type":"integer"}},"required":["ra_deg","dec_deg"],"type":"object","title":"vsx_cone_searchArguments"},"name":"vsx_cone_search","outputSchema":{"type":"object","additionalProperties":true,"title":"vsx_cone_searchDictOutput"}},{"annotations":{"idempotentHint":true,"openWorldHint":true,"readOnlyHint":true},"description":"Resolve a target name with SIMBAD, then list VSX variable stars around it.","inputSchema":{"properties":{"target":{"description":"Name of any object SIMBAD can resolve, e.g. 'M13', 'Vega', 'Pleiades'","title":"Target","type":"string"},"radius_deg":{"default":0.5,"description":"Search radius in degrees (max 5)","exclusiveMinimum":0,"maximum":5,"title":"Radius Deg","type":"number"},"max_mag":{"anyOf":[{"type":"number"},{"type":"null"}],"default":null,"description":"Only return stars reaching this magnitude or brighter at maximum","title":"Max Mag"},"limit":{"default":25,"description":"Maximum number of results","maximum":500,"minimum":1,"title":"Limit","type":"integer"}},"required":["target"],"type":"object","title":"variable_stars_nearArguments"},"name":"variable_stars_near","outputSchema":{"type":"object","additionalProperties":true,"title":"variable_stars_nearDictOutput"}},{"annotations":{"idempotentHint":true,"openWorldHint":true,"readOnlyHint":true},"description":"Sourced profile of a star, galaxy, nebula, cluster or planet: type, coordinates,\nmagnitudes, distance, size, common names, variability and constellation.\n\nA good first call for 'tell me about X' or 'how far/bright/big is X' when specific numbers\nmatter. Merges SIMBAD, OpenNGC and AAVSO VSX; planets get their current apparent details.\n","inputSchema":{"properties":{"name":{"description":"Planet, 'Moon', catalog name (M42, NGC 7000, Caldwell 14), common name (Ring Nebula) or SIMBAD identifier","title":"Name","type":"string"}},"required":["name"],"type":"object","title":"describe_objectArguments"},"name":"describe_object","outputSchema":{"type":"object","additionalProperties":true,"title":"describe_objectDictOutput"}},{"annotations":{"idempotentHint":true,"openWorldHint":true,"readOnlyHint":true},"description":"Find deep-sky objects by kind, constellation, brightness or size, brightest first.\n\nFor requests like 'bright planetary nebulae', 'Messier objects in Sagittarius' or\n'large galaxies visible tonight'. Covers NGC, IC, Messier and Caldwell extras (OpenNGC).\nFor a ranked plan of what to observe tonight, whats_up_tonight is usually better.\n","inputSchema":{"properties":{"object_type":{"anyOf":[{"enum":["asterism","dark_nebula","double_star","galaxy","globular_cluster","nebula","open_cluster","other","planetary_nebula","star","supernova_remnant"],"type":"string"},{"type":"null"}],"default":null,"description":"Kind of object to return","title":"Object Type"},"constellation":{"anyOf":[{"type":"string"},{"type":"null"}],"default":null,"description":"IAU constellation name or abbreviation, e.g. 'Sagittarius' or 'Sgr'","title":"Constellation"},"max_magnitude":{"anyOf":[{"type":"number"},{"type":"null"}],"default":null,"description":"Only objects at this magnitude or brighter","title":"Max Magnitude"},"min_size_arcmin":{"anyOf":[{"minimum":0,"type":"number"},{"type":"null"}],"default":null,"description":"Minimum major-axis size in arcminutes","title":"Min Size Arcmin"},"messier_only":{"default":false,"description":"Only Messier objects","title":"Messier Only","type":"boolean"},"name_contains":{"anyOf":[{"type":"string"},{"type":"null"}],"default":null,"description":"Substring of a catalog or common name, e.g. 'Veil'","title":"Name Contains"},"visible_tonight":{"default":false,"description":"Only objects that clear min_altitude during tonight's dark window (needs a location)","title":"Visible Tonight","type":"boolean"},"min_altitude":{"default":25.0,"description":"Minimum useful altitude in degrees","maximum":80,"minimum":0,"title":"Min Altitude","type":"number"},"date":{"anyOf":[{"type":"string"},{"type":"null"}],"default":null,"description":"Local date (YYYY-MM-DD) whose evening starts the night. Omit for tonight.","title":"Date"},"latitude":{"anyOf":[{"maximum":90,"minimum":-90,"type":"number"},{"type":"null"}],"default":null,"description":"Observer latitude in degrees (north positive). Omit to use place or the saved default.","title":"Latitude"},"longitude":{"anyOf":[{"maximum":180,"minimum":-180,"type":"number"},{"type":"null"}],"default":null,"description":"Observer longitude in degrees (east positive). Omit to use place or the saved default.","title":"Longitude"},"place":{"anyOf":[{"type":"string"},{"type":"null"}],"default":null,"description":"Place name to observe from instead of coordinates, e.g. 'Moab, Utah'.","title":"Place"},"limit":{"default":25,"description":"Maximum results","maximum":200,"minimum":1,"title":"Limit","type":"integer"}},"type":"object","title":"search_deep_skyArguments"},"name":"search_deep_sky","outputSchema":{"type":"object","additionalProperties":true,"title":"search_deep_skyDictOutput"}},{"annotations":{"idempotentHint":true,"openWorldHint":true,"readOnlyHint":true},"description":"Which IAU constellation an object or RA/Dec lies in, using the official boundaries.\n\nPlanets move between constellations, so use this rather than recalling where one is.\n","inputSchema":{"properties":{"target":{"anyOf":[{"type":"string"},{"type":"null"}],"default":null,"description":"Object name to locate; alternatively give ra_deg/dec_deg","title":"Target"},"ra_deg":{"anyOf":[{"exclusiveMaximum":360,"minimum":0,"type":"number"},{"type":"null"}],"default":null,"description":"Right ascension, decimal degrees (J2000)","title":"Ra Deg"},"dec_deg":{"anyOf":[{"maximum":90,"minimum":-90,"type":"number"},{"type":"null"}],"default":null,"description":"Declination, decimal degrees (J2000)","title":"Dec Deg"}},"type":"object","title":"identify_constellationArguments"},"name":"identify_constellation","outputSchema":{"type":"object","additionalProperties":true,"title":"identify_constellationDictOutput"}},{"annotations":{"idempotentHint":true,"openWorldHint":true,"readOnlyHint":true},"description":"Where an object is in the sky at a given moment from a given place.\n\nReturns altitude, azimuth, compass direction, airmass, RA/Dec (J2000 and of date),\nconstellation and magnitude. Use for 'where is Jupiter right now', 'which way do I look for\nM31 at 10pm' and similar; positions depend on time and place and should be computed.\n","inputSchema":{"properties":{"target":{"description":"Planet, 'Moon', catalog name (M42, NGC 7000, Caldwell 14), common name (Ring Nebula) or SIMBAD identifier","title":"Target","type":"string"},"time":{"anyOf":[{"type":"string"},{"type":"null"}],"default":null,"description":"ISO 8601 time; without an offset it is the observer's local time. Omit for now.","title":"Time"},"latitude":{"anyOf":[{"maximum":90,"minimum":-90,"type":"number"},{"type":"null"}],"default":null,"description":"Observer latitude in degrees (north positive). Omit to use place or the saved default.","title":"Latitude"},"longitude":{"anyOf":[{"maximum":180,"minimum":-180,"type":"number"},{"type":"null"}],"default":null,"description":"Observer longitude in degrees (east positive). Omit to use place or the saved default.","title":"Longitude"},"place":{"anyOf":[{"type":"string"},{"type":"null"}],"default":null,"description":"Place name to observe from instead of coordinates, e.g. 'Moab, Utah'.","title":"Place"}},"required":["target"],"type":"object","title":"get_positionArguments"},"name":"get_position","outputSchema":{"type":"object","additionalProperties":true,"title":"get_positionDictOutput"}},{"annotations":{"idempotentHint":true,"openWorldHint":true,"readOnlyHint":true},"description":"When an object rises, reaches its highest point, and sets on a given date and place.\n\nWorks for the Moon, planets, stars and deep-sky objects, and reports circumpolar or\nnever-rises cases. For the Sun's times and twilight, use get_twilight_times.\n","inputSchema":{"properties":{"target":{"description":"Planet, 'Moon', catalog name (M42, NGC 7000, Caldwell 14), common name (Ring Nebula) or SIMBAD identifier","title":"Target","type":"string"},"date":{"anyOf":[{"type":"string"},{"type":"null"}],"default":null,"description":"Local date (YYYY-MM-DD) whose evening starts the night. Omit for tonight.","title":"Date"},"latitude":{"anyOf":[{"maximum":90,"minimum":-90,"type":"number"},{"type":"null"}],"default":null,"description":"Observer latitude in degrees (north positive). Omit to use place or the saved default.","title":"Latitude"},"longitude":{"anyOf":[{"maximum":180,"minimum":-180,"type":"number"},{"type":"null"}],"default":null,"description":"Observer longitude in degrees (east positive). Omit to use place or the saved default.","title":"Longitude"},"place":{"anyOf":[{"type":"string"},{"type":"null"}],"default":null,"description":"Place name to observe from instead of coordinates, e.g. 'Moab, Utah'.","title":"Place"}},"required":["target"],"type":"object","title":"get_rise_set_transitArguments"},"name":"get_rise_set_transit","outputSchema":{"type":"object","additionalProperties":true,"title":"get_rise_set_transitDictOutput"}},{"annotations":{"idempotentHint":true,"openWorldHint":true,"readOnlyHint":true},"description":"Sunset, twilight stages, sunrise, when it gets fully dark, and moonrise/moonset.\n\nUse for 'when does it get dark', 'when is astronomical twilight' or 'how many hours of\nmoonless darkness tonight'.\n","inputSchema":{"properties":{"date":{"anyOf":[{"type":"string"},{"type":"null"}],"default":null,"description":"Local date (YYYY-MM-DD) whose evening starts the night. Omit for tonight.","title":"Date"},"latitude":{"anyOf":[{"maximum":90,"minimum":-90,"type":"number"},{"type":"null"}],"default":null,"description":"Observer latitude in degrees (north positive). Omit to use place or the saved default.","title":"Latitude"},"longitude":{"anyOf":[{"maximum":180,"minimum":-180,"type":"number"},{"type":"null"}],"default":null,"description":"Observer longitude in degrees (east positive). Omit to use place or the saved default.","title":"Longitude"},"place":{"anyOf":[{"type":"string"},{"type":"null"}],"default":null,"description":"Place name to observe from instead of coordinates, e.g. 'Moab, Utah'.","title":"Place"}},"type":"object","title":"get_twilight_timesArguments"},"name":"get_twilight_times","outputSchema":{"type":"object","additionalProperties":true,"title":"get_twilight_timesDictOutput"}},{"annotations":{"idempotentHint":true,"openWorldHint":true,"readOnlyHint":true},"description":"Current Moon phase and illumination, plus exact times of upcoming new, first quarter,\nfull and last quarter Moons.\n\nUse for 'when is the next full/new Moon' or planning dark-sky nights. Times use the saved\ndefault location's timezone, else UTC.\n","inputSchema":{"properties":{"start_date":{"anyOf":[{"type":"string"},{"type":"null"}],"default":null,"description":"First day (YYYY-MM-DD); omit for today","title":"Start Date"},"days":{"default":45,"description":"How many days of primary phases to list","maximum":400,"minimum":1,"title":"Days","type":"integer"}},"type":"object","title":"get_moon_phasesArguments"},"name":"get_moon_phases","outputSchema":{"type":"object","additionalProperties":true,"title":"get_moon_phasesDictOutput"}},{"annotations":{"idempotentHint":true,"openWorldHint":true,"readOnlyHint":true},"description":"Where the Sun, Moon and planets are now (or at a given time) and how they look.\n\nReturns magnitude, phase, apparent size, distance, constellation, morning/evening sky, and\nwith a location the altitude, direction and rise/transit/set times. Use for 'which planets\nare up', 'where is Mars' or 'is Venus a morning or evening star'.\n","inputSchema":{"properties":{"time":{"anyOf":[{"type":"string"},{"type":"null"}],"default":null,"description":"ISO 8601 time; without an offset it is the observer's local time. Omit for now.","title":"Time"},"latitude":{"anyOf":[{"maximum":90,"minimum":-90,"type":"number"},{"type":"null"}],"default":null,"description":"Observer latitude in degrees (north positive). Omit to use place or the saved default.","title":"Latitude"},"longitude":{"anyOf":[{"maximum":180,"minimum":-180,"type":"number"},{"type":"null"}],"default":null,"description":"Observer longitude in degrees (east positive). Omit to use place or the saved default.","title":"Longitude"},"place":{"anyOf":[{"type":"string"},{"type":"null"}],"default":null,"description":"Place name to observe from instead of coordinates, e.g. 'Moab, Utah'.","title":"Place"}},"type":"object","title":"get_planet_positionsArguments"},"name":"get_planet_positions","outputSchema":{"type":"object","additionalProperties":true,"title":"get_planet_positionsDictOutput"}},{"annotations":{"idempotentHint":true,"openWorldHint":true,"readOnlyHint":true},"description":"Ranked list of what is worth observing on a given night from a given place.\n\nUse for 'what can I see tonight', 'what should I point my telescope at' or 'what's up this\nweekend'. Considers darkness, the Moon, light pollution (atlas or user-supplied Bortle),\nterrain, and the equipment's reach. Each entry has difficulty, best time, altitude, direction\nand viewing window. Does not check clouds; pair with get_sky_forecast for that.\n","inputSchema":{"properties":{"date":{"anyOf":[{"type":"string"},{"type":"null"}],"default":null,"description":"Local date (YYYY-MM-DD) whose evening starts the night. Omit for tonight.","title":"Date"},"equipment":{"default":"telescope","description":"What the observer is using","enum":["naked_eye","binoculars","telescope"],"title":"Equipment","type":"string"},"aperture_mm":{"anyOf":[{"exclusiveMinimum":0,"maximum":2000,"type":"number"},{"type":"null"}],"default":null,"description":"Aperture in mm (defaults: binoculars 50, telescope 150)","title":"Aperture Mm"},"bortle":{"anyOf":[{"maximum":9,"minimum":1,"type":"integer"},{"type":"null"}],"default":null,"description":"Bortle class of the sky (1 pristine to 9 inner city). Omit to use the saved value or the light-pollution atlas.","title":"Bortle"},"include":{"default":"all","description":"Which kinds of targets","enum":["all","planets","deep_sky"],"title":"Include","type":"string"},"object_types":{"anyOf":[{"items":{"enum":["asterism","dark_nebula","double_star","galaxy","globular_cluster","nebula","open_cluster","other","planetary_nebula","star","supernova_remnant"],"type":"string"},"type":"array"},{"type":"null"}],"default":null,"description":"Restrict deep-sky results to these kinds","title":"Object Types"},"min_altitude":{"default":25.0,"description":"Minimum useful altitude in degrees","maximum":80,"minimum":0,"title":"Min Altitude","type":"number"},"max_results":{"default":20,"description":"Maximum targets","maximum":100,"minimum":1,"title":"Max Results","type":"integer"},"terrain":{"default":true,"description":"Account for hills and mountains on the local horizon (first use per location takes a few seconds)","title":"Terrain","type":"boolean"},"latitude":{"anyOf":[{"maximum":90,"minimum":-90,"type":"number"},{"type":"null"}],"default":null,"description":"Observer latitude in degrees (north positive). Omit to use place or the saved default.","title":"Latitude"},"longitude":{"anyOf":[{"maximum":180,"minimum":-180,"type":"number"},{"type":"null"}],"default":null,"description":"Observer longitude in degrees (east positive). Omit to use place or the saved default.","title":"Longitude"},"place":{"anyOf":[{"type":"string"},{"type":"null"}],"default":null,"description":"Place name to observe from instead of coordinates, e.g. 'Moab, Utah'.","title":"Place"}},"type":"object","title":"whats_up_tonightArguments"},"name":"whats_up_tonight","outputSchema":{"type":"object","additionalProperties":true,"title":"whats_up_tonightDictOutput"}},{"annotations":{"idempotentHint":true,"openWorldHint":true,"readOnlyHint":true},"description":"Whether one specific object can be seen on a given night, and when and where to look.\n\nUse for 'can I see Saturn tonight', 'is the Andromeda Galaxy visible from here' and similar,\neven when the question sounds casual. Returns yes/no with reasons (too low, behind terrain,\ntoo faint for the sky and equipment), difficulty, best time, direction and Moon interference.\nDoes not check clouds; use get_sky_forecast for that.\n","inputSchema":{"properties":{"target":{"description":"Planet, 'Moon', catalog name (M42, NGC 7000, Caldwell 14), common name (Ring Nebula) or SIMBAD identifier","title":"Target","type":"string"},"date":{"anyOf":[{"type":"string"},{"type":"null"}],"default":null,"description":"Local date (YYYY-MM-DD) whose evening starts the night. Omit for tonight.","title":"Date"},"equipment":{"default":"telescope","description":"What the observer is using","enum":["naked_eye","binoculars","telescope"],"title":"Equipment","type":"string"},"aperture_mm":{"anyOf":[{"exclusiveMinimum":0,"maximum":2000,"type":"number"},{"type":"null"}],"default":null,"description":"Aperture in mm (defaults: binoculars 50, telescope 150)","title":"Aperture Mm"},"bortle":{"anyOf":[{"maximum":9,"minimum":1,"type":"integer"},{"type":"null"}],"default":null,"description":"Bortle class of the sky (1 pristine to 9 inner city). Omit to use the saved value or the light-pollution atlas.","title":"Bortle"},"min_altitude":{"default":20.0,"description":"Minimum useful altitude in degrees","maximum":80,"minimum":0,"title":"Min Altitude","type":"number"},"terrain":{"default":true,"description":"Account for hills and mountains on the local horizon (first use per location takes a few seconds)","title":"Terrain","type":"boolean"},"latitude":{"anyOf":[{"maximum":90,"minimum":-90,"type":"number"},{"type":"null"}],"default":null,"description":"Observer latitude in degrees (north positive). Omit to use place or the saved default.","title":"Latitude"},"longitude":{"anyOf":[{"maximum":180,"minimum":-180,"type":"number"},{"type":"null"}],"default":null,"description":"Observer longitude in degrees (east positive). Omit to use place or the saved default.","title":"Longitude"},"place":{"anyOf":[{"type":"string"},{"type":"null"}],"default":null,"description":"Place name to observe from instead of coordinates, e.g. 'Moab, Utah'.","title":"Place"}},"required":["target"],"type":"object","title":"is_visible_tonightArguments"},"name":"is_visible_tonight","outputSchema":{"type":"object","additionalProperties":true,"title":"is_visible_tonightDictOutput"}},{"annotations":{"idempotentHint":true,"openWorldHint":true,"readOnlyHint":true},"description":"Compare upcoming nights and pick the best ones, for one target or for dark-sky observing.\n\nUse for 'which night this week is best for the Orion Nebula', 'when should I go out this\nmonth' or 'best night for Saturn'. Scores each night on how long the target is well placed\nin darkness, how high it gets, how much moonlight brightens the sky near it, and the cloud\nforecast. Clouds are only forecast about 16 days ahead, so later nights are ranked separately\non Moon and altitude alone. For one night's detail, follow up with is_visible_tonight and\nget_sky_forecast.\n","inputSchema":{"properties":{"target":{"anyOf":[{"type":"string"},{"type":"null"}],"default":null,"description":"Object to plan for: planet, 'Moon', catalog or common name. Omit to rate nights for general dark-sky observing.","title":"Target"},"start_date":{"anyOf":[{"type":"string"},{"type":"null"}],"default":null,"description":"First night to consider (YYYY-MM-DD); omit for tonight","title":"Start Date"},"days":{"default":30,"description":"How many nights to compare","maximum":60,"minimum":2,"title":"Days","type":"integer"},"min_altitude":{"default":25.0,"description":"Minimum useful altitude in degrees","maximum":80,"minimum":0,"title":"Min Altitude","type":"number"},"bortle":{"anyOf":[{"maximum":9,"minimum":1,"type":"integer"},{"type":"null"}],"default":null,"description":"Bortle class of the sky (1 pristine to 9 inner city). Omit to use the saved value or the light-pollution atlas.","title":"Bortle"},"latitude":{"anyOf":[{"maximum":90,"minimum":-90,"type":"number"},{"type":"null"}],"default":null,"description":"Observer latitude in degrees (north positive). Omit to use place or the saved default.","title":"Latitude"},"longitude":{"anyOf":[{"maximum":180,"minimum":-180,"type":"number"},{"type":"null"}],"default":null,"description":"Observer longitude in degrees (east positive). Omit to use place or the saved default.","title":"Longitude"},"place":{"anyOf":[{"type":"string"},{"type":"null"}],"default":null,"description":"Place name to observe from instead of coordinates, e.g. 'Moab, Utah'.","title":"Place"}},"type":"object","title":"best_night_this_monthArguments"},"name":"best_night_this_month","outputSchema":{"type":"object","additionalProperties":true,"title":"best_night_this_monthDictOutput"}},{"annotations":{"idempotentHint":true,"openWorldHint":true,"readOnlyHint":true},"description":"Upcoming weekends (Friday and Saturday nights) with little or no moonlight.\n\nUse for 'when is the next new-moon weekend', 'which weekends this summer are good for a\ndark-sky trip' or booking a campsite months ahead. With a location, counts the dark hours\neach night with the Moon down; without one, falls back to the Moon's illumination. Computed\noffline; weather is not considered.\n","inputSchema":{"properties":{"start_date":{"anyOf":[{"type":"string"},{"type":"null"}],"default":null,"description":"First day to consider (YYYY-MM-DD); omit for today","title":"Start Date"},"months":{"default":6,"description":"How many months ahead to search","maximum":24,"minimum":1,"title":"Months","type":"integer"},"min_moon_free_pct":{"default":70.0,"description":"Minimum share of the two nights' dark hours with the Moon below the horizon","maximum":100,"minimum":30,"title":"Min Moon Free Pct","type":"number"},"latitude":{"anyOf":[{"maximum":90,"minimum":-90,"type":"number"},{"type":"null"}],"default":null,"description":"Observer latitude in degrees (north positive). Omit to use place or the saved default.","title":"Latitude"},"longitude":{"anyOf":[{"maximum":180,"minimum":-180,"type":"number"},{"type":"null"}],"default":null,"description":"Observer longitude in degrees (east positive). Omit to use place or the saved default.","title":"Longitude"},"place":{"anyOf":[{"type":"string"},{"type":"null"}],"default":null,"description":"Place name to observe from instead of coordinates, e.g. 'Moab, Utah'.","title":"Place"}},"type":"object","title":"find_dark_moon_weekendsArguments"},"name":"find_dark_moon_weekends","outputSchema":{"type":"object","additionalProperties":true,"title":"find_dark_moon_weekendsDictOutput"}},{"annotations":{"idempotentHint":true,"openWorldHint":true,"readOnlyHint":true},"description":"Night-time observing weather: will it be clear, and when.\n\nHour-by-hour from sunset to sunrise: cloud cover by layer, humidity, dew point, wind and\nprecipitation chance, plus seeing and transparency about 3 days out. Summarises a 0-100\nscore, clear hours, the longest clear stretch and dew risk. Up to ~16 days ahead.\n","inputSchema":{"properties":{"date":{"anyOf":[{"type":"string"},{"type":"null"}],"default":null,"description":"Local date (YYYY-MM-DD) whose evening starts the night. Omit for tonight.","title":"Date"},"units":{"default":"metric","description":"Units for temperature and wind","enum":["metric","imperial"],"title":"Units","type":"string"},"latitude":{"anyOf":[{"maximum":90,"minimum":-90,"type":"number"},{"type":"null"}],"default":null,"description":"Observer latitude in degrees (north positive). Omit to use place or the saved default.","title":"Latitude"},"longitude":{"anyOf":[{"maximum":180,"minimum":-180,"type":"number"},{"type":"null"}],"default":null,"description":"Observer longitude in degrees (east positive). Omit to use place or the saved default.","title":"Longitude"},"place":{"anyOf":[{"type":"string"},{"type":"null"}],"default":null,"description":"Place name to observe from instead of coordinates, e.g. 'Moab, Utah'.","title":"Place"}},"type":"object","title":"get_sky_forecastArguments"},"name":"get_sky_forecast","outputSchema":{"type":"object","additionalProperties":true,"title":"get_sky_forecastDictOutput"}},{"annotations":{"idempotentHint":true,"openWorldHint":true,"readOnlyHint":true},"description":"What is dimming a night's sky besides clouds: wildfire smoke, dust and other aerosols.\n\nUse for 'is it smoky tonight', 'why is the sky so hazy' or 'will the Milky Way look washed\nout'. Hour-by-hour aerosol optical depth, dust and fine particles from sunset to sunrise,\nwith a transparency rating, the likely cause and the extra extinction in magnitudes. About\n5 days ahead. Clouds, humidity and seeing are in get_sky_forecast.\n","inputSchema":{"properties":{"date":{"anyOf":[{"type":"string"},{"type":"null"}],"default":null,"description":"Local date (YYYY-MM-DD) whose evening starts the night. Omit for tonight.","title":"Date"},"latitude":{"anyOf":[{"maximum":90,"minimum":-90,"type":"number"},{"type":"null"}],"default":null,"description":"Observer latitude in degrees (north positive). Omit to use place or the saved default.","title":"Latitude"},"longitude":{"anyOf":[{"maximum":180,"minimum":-180,"type":"number"},{"type":"null"}],"default":null,"description":"Observer longitude in degrees (east positive). Omit to use place or the saved default.","title":"Longitude"},"place":{"anyOf":[{"type":"string"},{"type":"null"}],"default":null,"description":"Place name to observe from instead of coordinates, e.g. 'Moab, Utah'.","title":"Place"}},"type":"object","title":"get_transparency_driversArguments"},"name":"get_transparency_drivers","outputSchema":{"type":"object","additionalProperties":true,"title":"get_transparency_driversDictOutput"}},{"annotations":{"idempotentHint":true,"openWorldHint":true,"readOnlyHint":true},"description":"Estimate the faintest stars visible for a sky and piece of equipment, including moonlight.\n\nUse for 'how faint can my telescope go' or 'how many stars will I see'. Sky darkness comes\nfrom the user's Bortle/SQM or the light-pollution atlas. A model estimate.\n","inputSchema":{"properties":{"equipment":{"default":"naked_eye","description":"What the observer is using","enum":["naked_eye","binoculars","telescope"],"title":"Equipment","type":"string"},"aperture_mm":{"anyOf":[{"exclusiveMinimum":0,"maximum":2000,"type":"number"},{"type":"null"}],"default":null,"description":"Aperture in mm (defaults: binoculars 50, telescope 150)","title":"Aperture Mm"},"bortle":{"anyOf":[{"maximum":9,"minimum":1,"type":"integer"},{"type":"null"}],"default":null,"description":"Bortle class of the sky (1 pristine to 9 inner city). Omit to use the saved value or the light-pollution atlas.","title":"Bortle"},"sqm":{"anyOf":[{"maximum":22.5,"minimum":15,"type":"number"},{"type":"null"}],"default":null,"description":"Measured sky brightness in mag/arcsec^2 (Sky Quality Meter)","title":"Sqm"},"time":{"anyOf":[{"type":"string"},{"type":"null"}],"default":null,"description":"ISO 8601 time; without an offset it is the observer's local time. Omit for now.","title":"Time"},"include_moon":{"default":true,"description":"Account for moonlight at the given time (or tonight's mid-darkness)","title":"Include Moon","type":"boolean"},"latitude":{"anyOf":[{"maximum":90,"minimum":-90,"type":"number"},{"type":"null"}],"default":null,"description":"Observer latitude in degrees (north positive). Omit to use place or the saved default.","title":"Latitude"},"longitude":{"anyOf":[{"maximum":180,"minimum":-180,"type":"number"},{"type":"null"}],"default":null,"description":"Observer longitude in degrees (east positive). Omit to use place or the saved default.","title":"Longitude"},"place":{"anyOf":[{"type":"string"},{"type":"null"}],"default":null,"description":"Place name to observe from instead of coordinates, e.g. 'Moab, Utah'.","title":"Place"}},"type":"object","title":"get_limiting_magnitudeArguments"},"name":"get_limiting_magnitude","outputSchema":{"type":"object","additionalProperties":true,"title":"get_limiting_magnitudeDictOutput"}},{"annotations":{"idempotentHint":true,"openWorldHint":true,"readOnlyHint":true},"description":"How light-polluted a location's sky is: atlas zone, sky brightness (mag/arcsec²), an\nestimated Bortle class, and the naked-eye limiting magnitude.\n\nUse for 'how dark is the sky at X', 'what Bortle class am I' or comparing sites. From the\n2025 Light Pollution Atlas (VIIRS satellite data); a modelled zenith value for a clear,\nmoonless night, not a measurement.\n","inputSchema":{"properties":{"latitude":{"anyOf":[{"maximum":90,"minimum":-90,"type":"number"},{"type":"null"}],"default":null,"description":"Observer latitude in degrees (north positive). Omit to use place or the saved default.","title":"Latitude"},"longitude":{"anyOf":[{"maximum":180,"minimum":-180,"type":"number"},{"type":"null"}],"default":null,"description":"Observer longitude in degrees (east positive). Omit to use place or the saved default.","title":"Longitude"},"place":{"anyOf":[{"type":"string"},{"type":"null"}],"default":null,"description":"Place name to observe from instead of coordinates, e.g. 'Moab, Utah'.","title":"Place"}},"type":"object","title":"get_light_pollutionArguments"},"name":"get_light_pollution","outputSchema":{"type":"object","additionalProperties":true,"title":"get_light_pollutionDictOutput"}},{"annotations":{"idempotentHint":true,"openWorldHint":true,"readOnlyHint":true},"description":"Suggest darker observing spots within a radius, each with nearby access points.\n\nUse for 'where can I go to see the Milky Way', 'darkest place within an hour of me' and\nsimilar. Ranks by the light-pollution atlas (darkest first, then closest), and keeps only\nspots with a mapped campground, viewpoint, picnic area, trailhead or named parking nearby\n(OpenStreetMap). Distances are straight-line; the user should check roads and access.\n","inputSchema":{"properties":{"radius_km":{"default":100,"description":"How far to search (straight-line km)","maximum":300,"minimum":10,"title":"Radius Km","type":"number"},"max_results":{"default":5,"description":"How many sites to suggest","maximum":10,"minimum":1,"title":"Max Results","type":"integer"},"min_separation_km":{"default":15,"description":"Minimum spacing between suggestions","maximum":100,"minimum":2,"title":"Min Separation Km","type":"number"},"latitude":{"anyOf":[{"maximum":90,"minimum":-90,"type":"number"},{"type":"null"}],"default":null,"description":"Observer latitude in degrees (north positive). Omit to use place or the saved default.","title":"Latitude"},"longitude":{"anyOf":[{"maximum":180,"minimum":-180,"type":"number"},{"type":"null"}],"default":null,"description":"Observer longitude in degrees (east positive). Omit to use place or the saved default.","title":"Longitude"},"place":{"anyOf":[{"type":"string"},{"type":"null"}],"default":null,"description":"Place name to observe from instead of coordinates, e.g. 'Moab, Utah'.","title":"Place"}},"type":"object","title":"find_dark_sitesArguments"},"name":"find_dark_sites","outputSchema":{"type":"object","additionalProperties":true,"title":"find_dark_sitesDictOutput"}},{"annotations":{"idempotentHint":true,"openWorldHint":true,"readOnlyHint":true},"description":"How high the surrounding terrain rises in each direction from an observing site.\n\nUse for 'will the mountains block my view to the south' or before planning low targets.\nComputed from a 90 m elevation model out to 35 km with Earth curvature and refraction;\ntrees and buildings are not included. whats_up_tonight and is_visible_tonight already\napply this automatically.\n","inputSchema":{"properties":{"latitude":{"anyOf":[{"maximum":90,"minimum":-90,"type":"number"},{"type":"null"}],"default":null,"description":"Observer latitude in degrees (north positive). Omit to use place or the saved default.","title":"Latitude"},"longitude":{"anyOf":[{"maximum":180,"minimum":-180,"type":"number"},{"type":"null"}],"default":null,"description":"Observer longitude in degrees (east positive). Omit to use place or the saved default.","title":"Longitude"},"place":{"anyOf":[{"type":"string"},{"type":"null"}],"default":null,"description":"Place name to observe from instead of coordinates, e.g. 'Moab, Utah'.","title":"Place"}},"type":"object","title":"get_horizon_profileArguments"},"name":"get_horizon_profile","outputSchema":{"type":"object","additionalProperties":true,"title":"get_horizon_profileDictOutput"}},{"annotations":{"idempotentHint":true,"openWorldHint":true,"readOnlyHint":true},"description":"Upcoming lunar eclipses, and solar eclipses visible from the observer's location.\n\nIncludes whether the Moon is up at mid-eclipse, local contact times and how much of the\nSun is covered. Use rather than recalling eclipse dates.\n","inputSchema":{"properties":{"years":{"default":10,"description":"How many years ahead to search for local solar eclipses","exclusiveMinimum":0,"maximum":30,"title":"Years","type":"number"},"lunar_count":{"default":6,"description":"How many upcoming lunar eclipses to list","maximum":30,"minimum":1,"title":"Lunar Count","type":"integer"},"latitude":{"anyOf":[{"maximum":90,"minimum":-90,"type":"number"},{"type":"null"}],"default":null,"description":"Observer latitude in degrees (north positive). Omit to use place or the saved default.","title":"Latitude"},"longitude":{"anyOf":[{"maximum":180,"minimum":-180,"type":"number"},{"type":"null"}],"default":null,"description":"Observer longitude in degrees (east positive). Omit to use place or the saved default.","title":"Longitude"},"place":{"anyOf":[{"type":"string"},{"type":"null"}],"default":null,"description":"Place name to observe from instead of coordinates, e.g. 'Moab, Utah'.","title":"Place"}},"type":"object","title":"get_eclipsesArguments"},"name":"get_eclipses","outputSchema":{"type":"object","additionalProperties":true,"title":"get_eclipsesDictOutput"}},{"annotations":{"idempotentHint":true,"openWorldHint":true,"readOnlyHint":true},"description":"Upcoming close pairings of planets in the sky (optionally with the Moon and bright stars).\n\nUse for 'when are Venus and Jupiter close together', 'any conjunctions this year', 'when\nis the Moon next to Saturn' or 'when does Mars pass Regulus'. Returns the moment of\nclosest approach, the separation, which body is to the north, the constellation, and\nwhether it is a morning or evening event. Computed offline for the centre of the Earth; a\nlocation only adds local times and whether the pair is up at that moment.\n","inputSchema":{"properties":{"start_date":{"anyOf":[{"type":"string"},{"type":"null"}],"default":null,"description":"First day (YYYY-MM-DD); omit for today","title":"Start Date"},"days":{"default":365,"description":"How many days ahead to search","maximum":1830,"minimum":1,"title":"Days","type":"integer"},"max_separation_deg":{"default":5.0,"description":"Only pairings at least this close","exclusiveMinimum":0,"maximum":15,"title":"Max Separation Deg","type":"number"},"include_moon":{"default":false,"description":"Also list the Moon passing each planet (about one per planet per month; best with a short range)","title":"Include Moon","type":"boolean"},"body":{"anyOf":[{"enum":["moon","mercury","venus","mars","jupiter","saturn","uranus","neptune"],"type":"string"},{"type":"null"}],"default":null,"description":"Only pairings that involve this body","title":"Body"},"min_elongation_deg":{"default":12.0,"description":"Skip pairings closer to the Sun than this; 0 keeps everything","maximum":60,"minimum":0,"title":"Min Elongation Deg","type":"number"},"include_stars":{"default":false,"description":"Also pair the planets (and the Moon, if included) with bright stars and clusters near the ecliptic: Regulus, Spica, Antares, Aldebaran, Pollux, the Pleiades, the Beehive and a few more","title":"Include Stars","type":"boolean"},"latitude":{"anyOf":[{"maximum":90,"minimum":-90,"type":"number"},{"type":"null"}],"default":null,"description":"Observer latitude in degrees (north positive). Omit to use place or the saved default.","title":"Latitude"},"longitude":{"anyOf":[{"maximum":180,"minimum":-180,"type":"number"},{"type":"null"}],"default":null,"description":"Observer longitude in degrees (east positive). Omit to use place or the saved default.","title":"Longitude"},"place":{"anyOf":[{"type":"string"},{"type":"null"}],"default":null,"description":"Place name to observe from instead of coordinates, e.g. 'Moab, Utah'.","title":"Place"}},"type":"object","title":"find_conjunctionsArguments"},"name":"find_conjunctions","outputSchema":{"type":"object","additionalProperties":true,"title":"find_conjunctionsDictOutput"}},{"annotations":{"idempotentHint":true,"openWorldHint":true,"readOnlyHint":true},"description":"When Mercury and Venus are farthest from the Sun in the sky: their best evening and morning showings.\n\nUse for 'when can I see Mercury', 'when is Venus highest in the evening' or 'best Mercury\napparition this year'. Gives the date, elongation, morning or evening sky, magnitude and\nphase, and with a location how high the planet stands at civil twilight, which is what\nmakes an apparition easy or hard. Computed offline.\n","inputSchema":{"properties":{"start_date":{"anyOf":[{"type":"string"},{"type":"null"}],"default":null,"description":"First day (YYYY-MM-DD); omit for today","title":"Start Date"},"days":{"default":365,"description":"How many days ahead to search","maximum":3650,"minimum":1,"title":"Days","type":"integer"},"planets":{"anyOf":[{"items":{"enum":["mercury","venus"],"type":"string"},"type":"array"},{"type":"null"}],"default":null,"description":"Mercury, Venus or both (default)","title":"Planets"},"latitude":{"anyOf":[{"maximum":90,"minimum":-90,"type":"number"},{"type":"null"}],"default":null,"description":"Observer latitude in degrees (north positive). Omit to use place or the saved default.","title":"Latitude"},"longitude":{"anyOf":[{"maximum":180,"minimum":-180,"type":"number"},{"type":"null"}],"default":null,"description":"Observer longitude in degrees (east positive). Omit to use place or the saved default.","title":"Longitude"},"place":{"anyOf":[{"type":"string"},{"type":"null"}],"default":null,"description":"Place name to observe from instead of coordinates, e.g. 'Moab, Utah'.","title":"Place"}},"type":"object","title":"find_greatest_elongationsArguments"},"name":"find_greatest_elongations","outputSchema":{"type":"object","additionalProperties":true,"title":"find_greatest_elongationsDictOutput"}},{"annotations":{"idempotentHint":true,"openWorldHint":true,"readOnlyHint":true},"description":"Upcoming oppositions of Mars, Jupiter, Saturn, Uranus and Neptune: when each planet is\nopposite the Sun, up all night, and at its biggest and brightest.\n\nUse for 'when is the next Mars opposition', 'when is Saturn best this year' or 'how close\ndoes Mars get in 2027'. Gives the date, constellation, magnitude, apparent size, distance,\nthe date of closest approach to Earth, and with a location how high the planet climbs.\nComputed offline; use rather than recalling dates.\n","inputSchema":{"properties":{"start_date":{"anyOf":[{"type":"string"},{"type":"null"}],"default":null,"description":"First day (YYYY-MM-DD); omit for today","title":"Start Date"},"years":{"default":3,"description":"How many years ahead to search (Mars comes to opposition only every 26 months)","exclusiveMinimum":0,"maximum":30,"title":"Years","type":"number"},"planets":{"anyOf":[{"items":{"enum":["mars","jupiter","saturn","uranus","neptune"],"type":"string"},"type":"array"},{"type":"null"}],"default":null,"description":"Restrict to these planets; omit for Mars through Neptune","title":"Planets"},"latitude":{"anyOf":[{"maximum":90,"minimum":-90,"type":"number"},{"type":"null"}],"default":null,"description":"Observer latitude in degrees (north positive). Omit to use place or the saved default.","title":"Latitude"},"longitude":{"anyOf":[{"maximum":180,"minimum":-180,"type":"number"},{"type":"null"}],"default":null,"description":"Observer longitude in degrees (east positive). Omit to use place or the saved default.","title":"Longitude"},"place":{"anyOf":[{"type":"string"},{"type":"null"}],"default":null,"description":"Place name to observe from instead of coordinates, e.g. 'Moab, Utah'.","title":"Place"}},"type":"object","title":"find_oppositionsArguments"},"name":"find_oppositions","outputSchema":{"type":"object","additionalProperties":true,"title":"find_oppositionsDictOutput"}},{"annotations":{"idempotentHint":true,"openWorldHint":true,"readOnlyHint":true},"description":"Where Io, Europa, Ganymede and Callisto are relative to Jupiter at a given moment.\n\nUse for 'which moon is which', 'why can I only see three moons' or 'is the Red Spot facing\nus right now'. Gives each moon's side and distance from the planet, whether it is in\ntransit, hidden behind Jupiter or in its shadow, any moon shadow on the disk, the\neast-to-west line-up, the central meridian longitudes and where the Great Red Spot is.\nComputed offline. For upcoming transits and eclipses, use get_jupiter_events.\n","inputSchema":{"properties":{"time":{"anyOf":[{"type":"string"},{"type":"null"}],"default":null,"description":"ISO 8601 time; without an offset it is the observer's local time. Omit for now.","title":"Time"},"grs_longitude":{"anyOf":[{"exclusiveMaximum":360,"minimum":0,"type":"number"},{"type":"null"}],"default":null,"description":"Great Red Spot's System II longitude, if you have a current measurement; omit to use the latest JUPOS value and its drift","title":"Grs Longitude"},"latitude":{"anyOf":[{"maximum":90,"minimum":-90,"type":"number"},{"type":"null"}],"default":null,"description":"Observer latitude in degrees (north positive). Omit to use place or the saved default.","title":"Latitude"},"longitude":{"anyOf":[{"maximum":180,"minimum":-180,"type":"number"},{"type":"null"}],"default":null,"description":"Observer longitude in degrees (east positive). Omit to use place or the saved default.","title":"Longitude"},"place":{"anyOf":[{"type":"string"},{"type":"null"}],"default":null,"description":"Place name to observe from instead of coordinates, e.g. 'Moab, Utah'.","title":"Place"}},"type":"object","title":"get_jupiter_moonsArguments"},"name":"get_jupiter_moons","outputSchema":{"type":"object","additionalProperties":true,"title":"get_jupiter_moonsDictOutput"}},{"annotations":{"idempotentHint":true,"openWorldHint":true,"readOnlyHint":true},"description":"Upcoming events of Jupiter's moons and Great Red Spot, in time order.\n\nUse for 'when is the next shadow transit', 'when can I see the Great Red Spot tonight' or\n'any Io transits this week' or 'mutual events tonight'. Lists moon transits, shadow\ntransits, occultations and eclipses (start and end), Red Spot transits, and in season the\nmoons occulting and eclipsing each other, good to a few minutes. With a location, each\nevent says whether Jupiter is up in a dark sky. Computed offline; the Red Spot's longitude\ncomes from the latest JUPOS measurement available.\n","inputSchema":{"properties":{"time":{"anyOf":[{"type":"string"},{"type":"null"}],"default":null,"description":"Start of the search, ISO 8601; without an offset it is the observer's local time. Omit for now.","title":"Time"},"hours":{"default":24,"description":"How many hours ahead to search","exclusiveMinimum":0,"maximum":240,"title":"Hours","type":"number"},"observable_only":{"default":false,"description":"Keep only events with Jupiter at least 10° up in a dark sky at the location","title":"Observable Only","type":"boolean"},"include_mutual_events":{"default":true,"description":"Include moons occulting and eclipsing each other (only in seasons around Jupiter's equinoxes, such as late 2026 to mid 2027)","title":"Include Mutual Events","type":"boolean"},"grs_longitude":{"anyOf":[{"exclusiveMaximum":360,"minimum":0,"type":"number"},{"type":"null"}],"default":null,"description":"Great Red Spot's System II longitude, if you have a current measurement; omit to use the latest JUPOS value and its drift","title":"Grs Longitude"},"latitude":{"anyOf":[{"maximum":90,"minimum":-90,"type":"number"},{"type":"null"}],"default":null,"description":"Observer latitude in degrees (north positive). Omit to use place or the saved default.","title":"Latitude"},"longitude":{"anyOf":[{"maximum":180,"minimum":-180,"type":"number"},{"type":"null"}],"default":null,"description":"Observer longitude in degrees (east positive). Omit to use place or the saved default.","title":"Longitude"},"place":{"anyOf":[{"type":"string"},{"type":"null"}],"default":null,"description":"Place name to observe from instead of coordinates, e.g. 'Moab, Utah'.","title":"Place"}},"type":"object","title":"get_jupiter_eventsArguments"},"name":"get_jupiter_events","outputSchema":{"type":"object","additionalProperties":true,"title":"get_jupiter_eventsDictOutput"}},{"annotations":{"idempotentHint":true,"openWorldHint":true,"readOnlyHint":true},"description":"Craters, mountains and other named features on the Moon's terminator at a given time.\n\nUse for 'what should I look at on the Moon tonight' or 'is Copernicus on the terminator'.\nThese are the features in low, raking sunlight, where shadows show the most relief. Lists\nthem largest first with the Sun's height at each and whether it is lunar sunrise or\nsunset there, plus the Moon's phase and terminator longitude. Feature names come from\nthe IAU/USGS gazetteer (downloaded once, about 24 MB).\n","inputSchema":{"properties":{"time":{"anyOf":[{"type":"string"},{"type":"null"}],"default":null,"description":"ISO 8601 time; without an offset it is the observer's local time. Omit for now.","title":"Time"},"min_diameter_km":{"default":20.0,"description":"Smallest feature to list","maximum":1000,"minimum":0,"title":"Min Diameter Km","type":"number"},"max_sun_altitude_deg":{"default":8.0,"description":"How far from the terminator to look, as the Sun's height above the feature","exclusiveMinimum":0,"maximum":30,"title":"Max Sun Altitude Deg","type":"number"},"feature_types":{"anyOf":[{"items":{"enum":["crater","mare","mons","rima","vallis","rupes","dorsum","catena","lacus","sinus","palus","promontorium","oceanus"],"type":"string"},"type":"array"},{"type":"null"}],"default":null,"description":"Restrict to these kinds of feature, e.g. ['crater'] or ['mons', 'rupes', 'vallis']","title":"Feature Types"},"limit":{"default":30,"description":"Maximum features","maximum":100,"minimum":1,"title":"Limit","type":"integer"},"latitude":{"anyOf":[{"maximum":90,"minimum":-90,"type":"number"},{"type":"null"}],"default":null,"description":"Observer latitude in degrees (north positive). Omit to use place or the saved default.","title":"Latitude"},"longitude":{"anyOf":[{"maximum":180,"minimum":-180,"type":"number"},{"type":"null"}],"default":null,"description":"Observer longitude in degrees (east positive). Omit to use place or the saved default.","title":"Longitude"},"place":{"anyOf":[{"type":"string"},{"type":"null"}],"default":null,"description":"Place name to observe from instead of coordinates, e.g. 'Moab, Utah'.","title":"Place"}},"type":"object","title":"get_lunar_terminatorArguments"},"name":"get_lunar_terminator","outputSchema":{"type":"object","additionalProperties":true,"title":"get_lunar_terminatorDictOutput"}},{"annotations":{"idempotentHint":true,"openWorldHint":true,"readOnlyHint":true},"description":"How the Moon is tipped toward the observer, and which limb features that brings into view.\n\nUse for 'is Mare Orientale visible tonight', 'what is the libration' or 'which limb is\nfavoured'. Gives libration in longitude and latitude, the favoured limb, and for 45 limb\nfeatures (Mare Orientale, Mare Humboldtianum, Bailly, the polar craters and others) how far\ninside the limb each sits, whether it is sunlit and whether the view is favourable.\nComputed offline.\n","inputSchema":{"properties":{"time":{"anyOf":[{"type":"string"},{"type":"null"}],"default":null,"description":"ISO 8601 time; without an offset it is the observer's local time. Omit for now.","title":"Time"},"latitude":{"anyOf":[{"maximum":90,"minimum":-90,"type":"number"},{"type":"null"}],"default":null,"description":"Observer latitude in degrees (north positive). Omit to use place or the saved default.","title":"Latitude"},"longitude":{"anyOf":[{"maximum":180,"minimum":-180,"type":"number"},{"type":"null"}],"default":null,"description":"Observer longitude in degrees (east positive). Omit to use place or the saved default.","title":"Longitude"},"place":{"anyOf":[{"type":"string"},{"type":"null"}],"default":null,"description":"Place name to observe from instead of coordinates, e.g. 'Moab, Utah'.","title":"Place"}},"type":"object","title":"get_moon_librationArguments"},"name":"get_moon_libration","outputSchema":{"type":"object","additionalProperties":true,"title":"get_moon_librationDictOutput"}},{"annotations":{"idempotentHint":true,"openWorldHint":true,"readOnlyHint":true},"description":"Which comets are bright enough to see now, or how one comet will look over the coming weeks.\n\nUse for 'are there any comets visible', 'can I see comet X tonight' or 'when is comet X at\nits best'. Without a comet: the comets at or brighter than max_magnitude, brightest first,\nwith constellation, morning or evening sky, the equipment needed and, with a location, the\nbest time and altitude tonight. Brightness is from COBS observer reports where available,\notherwise JPL's prediction. With a comet: tonight's view plus a day-by-day trend (JPL\nHorizons). Comet brightness is hard to predict; present magnitudes as estimates.\n","inputSchema":{"properties":{"comet":{"anyOf":[{"type":"string"},{"type":"null"}],"default":null,"description":"A comet to look at, e.g. '12P', 'C/2025 R2', 'Tempel 2'. Omit to list the bright comets now.","title":"Comet"},"max_magnitude":{"default":12.0,"description":"Without a comet: only list comets at least this bright","maximum":18,"minimum":0,"title":"Max Magnitude","type":"number"},"limit":{"default":10,"description":"Without a comet: maximum comets to list","maximum":30,"minimum":1,"title":"Limit","type":"integer"},"days":{"default":30,"description":"With a comet: how many days of brightness and position trend","maximum":120,"minimum":1,"title":"Days","type":"integer"},"date":{"anyOf":[{"type":"string"},{"type":"null"}],"default":null,"description":"Local date (YYYY-MM-DD) whose evening starts the night. Omit for tonight.","title":"Date"},"latitude":{"anyOf":[{"maximum":90,"minimum":-90,"type":"number"},{"type":"null"}],"default":null,"description":"Observer latitude in degrees (north positive). Omit to use place or the saved default.","title":"Latitude"},"longitude":{"anyOf":[{"maximum":180,"minimum":-180,"type":"number"},{"type":"null"}],"default":null,"description":"Observer longitude in degrees (east positive). Omit to use place or the saved default.","title":"Longitude"},"place":{"anyOf":[{"type":"string"},{"type":"null"}],"default":null,"description":"Place name to observe from instead of coordinates, e.g. 'Moab, Utah'.","title":"Place"}},"type":"object","title":"get_comet_visibilityArguments"},"name":"get_comet_visibility","outputSchema":{"type":"object","additionalProperties":true,"title":"get_comet_visibilityDictOutput"}},{"annotations":{"idempotentHint":true,"openWorldHint":true,"readOnlyHint":true},"description":"Asteroids bright enough for binoculars or a small telescope now, brightest first.\n\nUse for 'which asteroids can I see', 'is Vesta visible' or 'asteroids near opposition'.\nGives magnitude, constellation, how far from the Sun in the sky (near 180° means up all\nnight) and with a location the best time and altitude tonight. Positions and magnitudes\nfrom JPL Horizons; for a night-by-night table use get_asteroid_ephemeris.\n","inputSchema":{"properties":{"max_magnitude":{"default":10.0,"description":"Only asteroids at least this bright","maximum":12,"minimum":4,"title":"Max Magnitude","type":"number"},"limit":{"default":10,"description":"Maximum asteroids","maximum":30,"minimum":1,"title":"Limit","type":"integer"},"date":{"anyOf":[{"type":"string"},{"type":"null"}],"default":null,"description":"Local date (YYYY-MM-DD) whose evening starts the night. Omit for tonight.","title":"Date"},"latitude":{"anyOf":[{"maximum":90,"minimum":-90,"type":"number"},{"type":"null"}],"default":null,"description":"Observer latitude in degrees (north positive). Omit to use place or the saved default.","title":"Latitude"},"longitude":{"anyOf":[{"maximum":180,"minimum":-180,"type":"number"},{"type":"null"}],"default":null,"description":"Observer longitude in degrees (east positive). Omit to use place or the saved default.","title":"Longitude"},"place":{"anyOf":[{"type":"string"},{"type":"null"}],"default":null,"description":"Place name to observe from instead of coordinates, e.g. 'Moab, Utah'.","title":"Place"}},"type":"object","title":"find_bright_asteroidsArguments"},"name":"find_bright_asteroids","outputSchema":{"type":"object","additionalProperties":true,"title":"find_bright_asteroidsDictOutput"}},{"annotations":{"idempotentHint":true,"openWorldHint":true,"readOnlyHint":true},"description":"Where an asteroid (or comet) is and how bright, as a table over time, from JPL Horizons.\n\nUse for 'where is Vesta', 'how bright will Apophis get' or 'finder positions for asteroid X'.\nRows give RA/Dec, constellation, magnitude, motion across the sky, distances and elongation\nfrom the Sun; with a location, also altitude and direction. Also returns the object's\norbit class, size, albedo and whether it is a near-Earth or potentially hazardous object.\nUp to 500 rows.\n","inputSchema":{"properties":{"target":{"description":"Asteroid or comet name, number or designation, e.g. 'Vesta', '4', 'Apophis', '2024 YR4', '12P'","title":"Target","type":"string"},"start":{"anyOf":[{"type":"string"},{"type":"null"}],"default":null,"description":"First time, ISO 8601; without an offset it is the observer's local time. Omit for now.","title":"Start"},"days":{"default":7,"description":"How many days to cover","exclusiveMinimum":0,"maximum":366,"title":"Days","type":"number"},"step_hours":{"default":24,"description":"Hours between rows (24 for daily)","maximum":720,"minimum":0.25,"title":"Step Hours","type":"number"},"latitude":{"anyOf":[{"maximum":90,"minimum":-90,"type":"number"},{"type":"null"}],"default":null,"description":"Observer latitude in degrees (north positive). Omit to use place or the saved default.","title":"Latitude"},"longitude":{"anyOf":[{"maximum":180,"minimum":-180,"type":"number"},{"type":"null"}],"default":null,"description":"Observer longitude in degrees (east positive). Omit to use place or the saved default.","title":"Longitude"},"place":{"anyOf":[{"type":"string"},{"type":"null"}],"default":null,"description":"Place name to observe from instead of coordinates, e.g. 'Moab, Utah'.","title":"Place"}},"required":["target"],"type":"object","title":"get_asteroid_ephemerisArguments"},"name":"get_asteroid_ephemeris","outputSchema":{"type":"object","additionalProperties":true,"title":"get_asteroid_ephemerisDictOutput"}},{"annotations":{"idempotentHint":true,"openWorldHint":true,"readOnlyHint":true},"description":"Asteroids and comets passing close to Earth, in time order (JPL Close Approach Data).\n\nUse for 'any asteroids passing Earth this month', 'how close did X come' or 'next close\napproach of Apophis'. Gives time, distance in lunar distances and km, speed, absolute\nmagnitude and size. A location only adds local times. Whether one is observable needs\nget_asteroid_ephemeris.\n","inputSchema":{"properties":{"start_date":{"anyOf":[{"type":"string"},{"type":"null"}],"default":null,"description":"First day (YYYY-MM-DD), may be in the past; omit for now","title":"Start Date"},"days":{"default":60,"description":"How many days to search","maximum":3650,"minimum":1,"title":"Days","type":"integer"},"max_distance_lunar":{"default":10,"description":"Only approaches closer than this many lunar distances (1 LD = 384,399 km)","exclusiveMinimum":0,"maximum":200,"title":"Max Distance Lunar","type":"number"},"max_absolute_magnitude":{"anyOf":[{"maximum":35,"minimum":5,"type":"number"},{"type":"null"}],"default":null,"description":"Only objects with H at or below this (smaller H is bigger: H 22 is roughly 100-250 m)","title":"Max Absolute Magnitude"},"limit":{"default":25,"description":"Maximum approaches","maximum":100,"minimum":1,"title":"Limit","type":"integer"},"latitude":{"anyOf":[{"maximum":90,"minimum":-90,"type":"number"},{"type":"null"}],"default":null,"description":"Observer latitude in degrees (north positive). Omit to use place or the saved default.","title":"Latitude"},"longitude":{"anyOf":[{"maximum":180,"minimum":-180,"type":"number"},{"type":"null"}],"default":null,"description":"Observer longitude in degrees (east positive). Omit to use place or the saved default.","title":"Longitude"},"place":{"anyOf":[{"type":"string"},{"type":"null"}],"default":null,"description":"Place name to observe from instead of coordinates, e.g. 'Moab, Utah'.","title":"Place"}},"type":"object","title":"find_close_approachesArguments"},"name":"find_close_approaches","outputSchema":{"type":"object","additionalProperties":true,"title":"find_close_approachesDictOutput"}},{"annotations":{"idempotentHint":true,"openWorldHint":true,"readOnlyHint":true},"description":"Large fireballs (bolides) detected by US government sensors, newest first (CNEOS).\n\nUse for 'was that huge fireball last night recorded', 'recent bolides near me' or 'how often\ndo big fireballs happen'. Gives time, position, altitude, speed and energy; with a location,\nthe distance and whether it was above the observer's horizon. Only metre-scale and larger\nimpacts are listed, and reports lag by days to weeks; ordinary bright meteors aren't here.\n","inputSchema":{"properties":{"days":{"default":365,"description":"How many days back to look","maximum":12000,"minimum":1,"title":"Days","type":"integer"},"limit":{"default":20,"description":"Maximum events, newest first","maximum":100,"minimum":1,"title":"Limit","type":"integer"},"max_distance_km":{"anyOf":[{"exclusiveMinimum":0,"maximum":20000,"type":"number"},{"type":"null"}],"default":null,"description":"Only events within this distance of the observer","title":"Max Distance Km"},"latitude":{"anyOf":[{"maximum":90,"minimum":-90,"type":"number"},{"type":"null"}],"default":null,"description":"Observer latitude in degrees (north positive). Omit to use place or the saved default.","title":"Latitude"},"longitude":{"anyOf":[{"maximum":180,"minimum":-180,"type":"number"},{"type":"null"}],"default":null,"description":"Observer longitude in degrees (east positive). Omit to use place or the saved default.","title":"Longitude"},"place":{"anyOf":[{"type":"string"},{"type":"null"}],"default":null,"description":"Place name to observe from instead of coordinates, e.g. 'Moab, Utah'.","title":"Place"}},"type":"object","title":"get_fireball_reportsArguments"},"name":"get_fireball_reports","outputSchema":{"type":"object","additionalProperties":true,"title":"get_fireball_reportsDictOutput"}},{"annotations":{"idempotentHint":true,"openWorldHint":true,"readOnlyHint":true},"description":"When the International Space Station will be visible from the observer's location.\n\nUse for 'when can I see the ISS' or 'is the space station going over tonight'. Lists passes\nwhere the ISS is sunlit against a dark sky: where it appears, its highest point and where it\nvanishes (often fading into Earth's shadow mid-sky), with local times to the second and an\nestimated magnitude. Computed from CelesTrak orbital elements with SGP4.\n","inputSchema":{"properties":{"days":{"default":5,"description":"How many days ahead (predictions drift after a few days)","exclusiveMinimum":0,"maximum":10,"title":"Days","type":"number"},"min_altitude":{"default":10,"description":"Only count the satellite while at least this high, degrees","maximum":80,"minimum":0,"title":"Min Altitude","type":"number"},"latitude":{"anyOf":[{"maximum":90,"minimum":-90,"type":"number"},{"type":"null"}],"default":null,"description":"Observer latitude in degrees (north positive). Omit to use place or the saved default.","title":"Latitude"},"longitude":{"anyOf":[{"maximum":180,"minimum":-180,"type":"number"},{"type":"null"}],"default":null,"description":"Observer longitude in degrees (east positive). Omit to use place or the saved default.","title":"Longitude"},"place":{"anyOf":[{"type":"string"},{"type":"null"}],"default":null,"description":"Place name to observe from instead of coordinates, e.g. 'Moab, Utah'.","title":"Place"}},"type":"object","title":"get_iss_passesArguments"},"name":"get_iss_passes","outputSchema":{"type":"object","additionalProperties":true,"title":"get_iss_passesDictOutput"}},{"annotations":{"idempotentHint":true,"openWorldHint":true,"readOnlyHint":true},"description":"Upcoming passes of any Earth satellite over the observer, by name or NORAD number.\n\nUse for 'when does Hubble pass over', 'Tiangong passes this week' or a specific NORAD id.\nBy default only visible passes (satellite sunlit, observer's sky dark), with where it\nappears, peaks and vanishes. Brightness is estimated for the ISS, Tiangong, Hubble and\nStarlink, or any satellite given standard_magnitude. For the ISS, get_iss_passes is simpler.\n","inputSchema":{"properties":{"satellite":{"description":"NORAD catalog number, a common name ('ISS', 'Tiangong', 'Hubble') or a CelesTrak name ('STARLINK-1234', 'NOAA 19')","title":"Satellite","type":"string"},"days":{"default":5,"description":"How many days ahead (predictions drift after a few days)","exclusiveMinimum":0,"maximum":10,"title":"Days","type":"number"},"min_altitude":{"default":10,"description":"Only count the satellite while at least this high, degrees","maximum":80,"minimum":0,"title":"Min Altitude","type":"number"},"include_daylight":{"default":false,"description":"Also list passes that can't be seen (daylight or Earth's shadow), e.g. for radio","title":"Include Daylight","type":"boolean"},"standard_magnitude":{"anyOf":[{"maximum":15,"minimum":-5,"type":"number"},{"type":"null"}],"default":null,"description":"Satellite's magnitude at 1000 km and half phase, if known; enables brightness estimates","title":"Standard Magnitude"},"latitude":{"anyOf":[{"maximum":90,"minimum":-90,"type":"number"},{"type":"null"}],"default":null,"description":"Observer latitude in degrees (north positive). Omit to use place or the saved default.","title":"Latitude"},"longitude":{"anyOf":[{"maximum":180,"minimum":-180,"type":"number"},{"type":"null"}],"default":null,"description":"Observer longitude in degrees (east positive). Omit to use place or the saved default.","title":"Longitude"},"place":{"anyOf":[{"type":"string"},{"type":"null"}],"default":null,"description":"Place name to observe from instead of coordinates, e.g. 'Moab, Utah'.","title":"Place"}},"required":["satellite"],"type":"object","title":"get_satellite_passesArguments"},"name":"get_satellite_passes","outputSchema":{"type":"object","additionalProperties":true,"title":"get_satellite_passesDictOutput"}},{"annotations":{"idempotentHint":true,"openWorldHint":true,"readOnlyHint":true},"description":"Satellites above the observer right now (or at a given time): where each is and where it's heading.\n\nUse for 'what is that moving light' or 'what satellites are up now'. Lists each satellite's\naltitude, direction, distance, whether it is lit by the Sun, estimated magnitude where known,\nand where it will leave view (setting or fading into Earth's shadow). Brightest first.\n","inputSchema":{"properties":{"time":{"anyOf":[{"type":"string"},{"type":"null"}],"default":null,"description":"ISO 8601 time; without an offset it is the observer's local time. Omit for now.","title":"Time"},"group":{"default":"visual","description":"Which satellites: visual (about 150 of the brightest), stations, starlink, or active (all ~16,000; slower first download)","enum":["visual","stations","starlink","active"],"title":"Group","type":"string"},"min_altitude":{"default":10,"description":"Only count the satellite while at least this high, degrees","maximum":80,"minimum":0,"title":"Min Altitude","type":"number"},"visible_only":{"default":true,"description":"Only satellites that are sunlit while the observer's sky is dark","title":"Visible Only","type":"boolean"},"limit":{"default":25,"description":"Maximum satellites","maximum":200,"minimum":1,"title":"Limit","type":"integer"},"latitude":{"anyOf":[{"maximum":90,"minimum":-90,"type":"number"},{"type":"null"}],"default":null,"description":"Observer latitude in degrees (north positive). Omit to use place or the saved default.","title":"Latitude"},"longitude":{"anyOf":[{"maximum":180,"minimum":-180,"type":"number"},{"type":"null"}],"default":null,"description":"Observer longitude in degrees (east positive). Omit to use place or the saved default.","title":"Longitude"},"place":{"anyOf":[{"type":"string"},{"type":"null"}],"default":null,"description":"Place name to observe from instead of coordinates, e.g. 'Moab, Utah'.","title":"Place"}},"type":"object","title":"find_satellites_overheadArguments"},"name":"find_satellites_overhead","outputSchema":{"type":"object","additionalProperties":true,"title":"find_satellites_overheadDictOutput"}},{"annotations":{"idempotentHint":true,"openWorldHint":true,"readOnlyHint":true},"description":"When the ISS (or another satellite) crosses the face of the Sun or Moon near the observer.\n\nUse for 'can I photograph the ISS crossing the Moon' or 'any ISS solar transits near me'.\nA transit is seen only within a few kilometres of a centerline, so each event gives the\nnearest point on that line (distance, direction, coordinates), the path width, the time to\nthe millisecond, how long the crossing lasts (about a second), and whether it transits\nfrom the observer's own spot. Predictions shift by kilometres as orbits change; recheck a\nday before. Solar transits need a proper solar filter.\n","inputSchema":{"properties":{"days":{"default":7,"description":"How many days ahead (predictions drift after a few days)","exclusiveMinimum":0,"maximum":10,"title":"Days","type":"number"},"max_distance_km":{"default":50,"description":"How far you would travel to the centerline","exclusiveMinimum":0,"maximum":300,"title":"Max Distance Km","type":"number"},"bodies":{"anyOf":[{"items":{"enum":["Sun","Moon"],"type":"string"},"type":"array"},{"type":"null"}],"default":null,"description":"Sun, Moon or both (default)","title":"Bodies"},"min_altitude":{"default":10,"description":"Lowest Sun or Moon altitude worth considering, degrees","maximum":80,"minimum":0,"title":"Min Altitude","type":"number"},"satellite":{"default":"ISS","description":"Satellite to check; the ISS by default, or 'Tiangong', a name or a NORAD number","title":"Satellite","type":"string"},"latitude":{"anyOf":[{"maximum":90,"minimum":-90,"type":"number"},{"type":"null"}],"default":null,"description":"Observer latitude in degrees (north positive). Omit to use place or the saved default.","title":"Latitude"},"longitude":{"anyOf":[{"maximum":180,"minimum":-180,"type":"number"},{"type":"null"}],"default":null,"description":"Observer longitude in degrees (east positive). Omit to use place or the saved default.","title":"Longitude"},"place":{"anyOf":[{"type":"string"},{"type":"null"}],"default":null,"description":"Place name to observe from instead of coordinates, e.g. 'Moab, Utah'.","title":"Place"}},"type":"object","title":"predict_iss_transitArguments"},"name":"predict_iss_transit","outputSchema":{"type":"object","additionalProperties":true,"title":"predict_iss_transitDictOutput"}},{"annotations":{"idempotentHint":true,"openWorldHint":true,"readOnlyHint":true},"description":"Recently launched Starlink batches and when their 'train' of satellites passes over.\n\nUse for 'I saw a line of lights moving across the sky' or 'when can I see a Starlink\ntrain'. For each batch launched in the last few weeks: satellite count, altitude, how\nstretched out the line is, and visible passes with times for the first and last satellite.\nTrains are best in the first days after launch and disperse within a few weeks.\n","inputSchema":{"properties":{"days":{"default":3,"description":"How many days ahead to look for passes","exclusiveMinimum":0,"maximum":7,"title":"Days","type":"number"},"max_launch_age_days":{"default":21,"description":"Only batches launched within this many days","exclusiveMinimum":0,"maximum":30,"title":"Max Launch Age Days","type":"number"},"min_altitude":{"default":10,"description":"Only count the satellite while at least this high, degrees","maximum":80,"minimum":0,"title":"Min Altitude","type":"number"},"latitude":{"anyOf":[{"maximum":90,"minimum":-90,"type":"number"},{"type":"null"}],"default":null,"description":"Observer latitude in degrees (north positive). Omit to use place or the saved default.","title":"Latitude"},"longitude":{"anyOf":[{"maximum":180,"minimum":-180,"type":"number"},{"type":"null"}],"default":null,"description":"Observer longitude in degrees (east positive). Omit to use place or the saved default.","title":"Longitude"},"place":{"anyOf":[{"type":"string"},{"type":"null"}],"default":null,"description":"Place name to observe from instead of coordinates, e.g. 'Moab, Utah'.","title":"Place"}},"type":"object","title":"get_starlink_trainsArguments"},"name":"get_starlink_trains","outputSchema":{"type":"object","additionalProperties":true,"title":"get_starlink_trainsDictOutput"}},{"annotations":{"idempotentHint":true,"openWorldHint":true,"readOnlyHint":true},"description":"Every catalogued pair in a double or multiple star, and whether a telescope can split each.\n\nUse for 'can my 4-inch split epsilon Lyrae', 'how far apart are Albireo's stars' or 'what\nare the components of Castor'. From the Washington Double Star catalog: separation and\nposition angle at the latest measurement, magnitudes and spectral types; with an aperture,\na split verdict (easy/moderate/challenging) and a magnification to try.\n","inputSchema":{"properties":{"name":{"description":"Star name ('Albireo', 'epsilon Lyrae', 'Mizar'), WDS id ('19307+2758') or discoverer designation ('STF 2382')","title":"Name","type":"string"},"aperture_mm":{"anyOf":[{"exclusiveMinimum":0,"maximum":2000,"type":"number"},{"type":"null"}],"default":null,"description":"Telescope aperture in mm, to judge whether each pair can be split","title":"Aperture Mm"},"seeing_arcsec":{"default":2.0,"description":"Typical seeing (star blur) in arcseconds: 1 excellent, 2 average, 3-4 poor","maximum":6,"minimum":0.3,"title":"Seeing Arcsec","type":"number"}},"required":["name"],"type":"object","title":"get_double_starArguments"},"name":"get_double_star","outputSchema":{"type":"object","additionalProperties":true,"title":"get_double_starDictOutput"}},{"annotations":{"idempotentHint":true,"openWorldHint":true,"readOnlyHint":true},"description":"Double stars a given telescope can split, brightest first, optionally just tonight's.\n\nUse for 'good double stars for my 6-inch tonight' or 'a challenging double for a 4-inch'.\nSearches the Washington Double Star catalog for pairs above the Dawes limit and the seeing,\nallowing for brightness differences, and names each primary from SIMBAD.\n","inputSchema":{"properties":{"aperture_mm":{"default":100,"description":"Telescope aperture in mm","exclusiveMinimum":0,"maximum":2000,"title":"Aperture Mm","type":"number"},"seeing_arcsec":{"default":2.0,"description":"Typical seeing (star blur) in arcseconds: 1 excellent, 2 average, 3-4 poor","maximum":6,"minimum":0.3,"title":"Seeing Arcsec","type":"number"},"max_primary_magnitude":{"default":6.5,"description":"Only pairs whose brighter star is at least this bright","maximum":10,"minimum":-2,"title":"Max Primary Magnitude","type":"number"},"max_separation_arcsec":{"default":60,"description":"Skip pairs wider than this","exclusiveMinimum":0,"maximum":300,"title":"Max Separation Arcsec","type":"number"},"constellation":{"anyOf":[{"type":"string"},{"type":"null"}],"default":null,"description":"Only pairs in this constellation (name or abbreviation)","title":"Constellation"},"challenging_only":{"default":false,"description":"Only pairs near the telescope's limit, as a test","title":"Challenging Only","type":"boolean"},"visible_tonight":{"default":true,"description":"Only pairs that climb above min_altitude in tonight's dark sky (needs a location)","title":"Visible Tonight","type":"boolean"},"min_altitude":{"default":25.0,"description":"Minimum useful altitude in degrees","maximum":80,"minimum":0,"title":"Min Altitude","type":"number"},"date":{"anyOf":[{"type":"string"},{"type":"null"}],"default":null,"description":"Local date (YYYY-MM-DD) whose evening starts the night. Omit for tonight.","title":"Date"},"latitude":{"anyOf":[{"maximum":90,"minimum":-90,"type":"number"},{"type":"null"}],"default":null,"description":"Observer latitude in degrees (north positive). Omit to use place or the saved default.","title":"Latitude"},"longitude":{"anyOf":[{"maximum":180,"minimum":-180,"type":"number"},{"type":"null"}],"default":null,"description":"Observer longitude in degrees (east positive). Omit to use place or the saved default.","title":"Longitude"},"place":{"anyOf":[{"type":"string"},{"type":"null"}],"default":null,"description":"Place name to observe from instead of coordinates, e.g. 'Moab, Utah'.","title":"Place"},"limit":{"default":20,"description":"Maximum pairs","maximum":50,"minimum":1,"title":"Limit","type":"integer"}},"type":"object","title":"find_splittable_doublesArguments"},"name":"find_splittable_doubles","outputSchema":{"type":"object","additionalProperties":true,"title":"find_splittable_doublesDictOutput"}},{"annotations":{"idempotentHint":true,"openWorldHint":true,"readOnlyHint":true},"description":"How bright a variable star is right now, from recent AAVSO observations.\n\nUse for 'is SS Cyg in outburst', 'how bright is Mira now', 'when is Algol's next eclipse' or\n'is chi Cygni near maximum'. Gives the latest observation, medians by band over the last week,\nthe recent trend, where it sits in its range, and predicted maxima or eclipses from the period.\n","inputSchema":{"properties":{"name":{"description":"Variable star name: 'Mira', 'R Leo', 'SS Cyg', 'Algol', 'chi Cyg'","title":"Name","type":"string"},"days":{"default":30,"description":"How many days of observations to summarise","maximum":365,"minimum":1,"title":"Days","type":"integer"},"latitude":{"anyOf":[{"maximum":90,"minimum":-90,"type":"number"},{"type":"null"}],"default":null,"description":"Observer latitude in degrees (north positive). Omit to use place or the saved default.","title":"Latitude"},"longitude":{"anyOf":[{"maximum":180,"minimum":-180,"type":"number"},{"type":"null"}],"default":null,"description":"Observer longitude in degrees (east positive). Omit to use place or the saved default.","title":"Longitude"},"place":{"anyOf":[{"type":"string"},{"type":"null"}],"default":null,"description":"Place name to observe from instead of coordinates, e.g. 'Moab, Utah'.","title":"Place"}},"required":["name"],"type":"object","title":"get_variable_star_statusArguments"},"name":"get_variable_star_status","outputSchema":{"type":"object","additionalProperties":true,"title":"get_variable_star_statusDictOutput"}},{"annotations":{"idempotentHint":true,"openWorldHint":true,"readOnlyHint":true},"description":"A variable star's light curve from AAVSO observations, binned by band.\n\nUse for 'plot Mira's brightness this year', 'how did SS Cyg behave lately' or to compare a\nstar's cycle with its prediction. Each point is the median magnitude in a time bin, with\nthe count of observations; up to two years.\n","inputSchema":{"properties":{"name":{"description":"Variable star name, e.g. 'Mira', 'SS Cyg', 'R CrB'","title":"Name","type":"string"},"days":{"default":365,"description":"How many days back","maximum":730,"minimum":1,"title":"Days","type":"integer"},"bands":{"anyOf":[{"items":{"type":"string"},"type":"array"},{"type":"null"}],"default":null,"description":"Only these AAVSO bands, e.g. ['Vis.', 'V']; omit for all","title":"Bands"},"bin_days":{"anyOf":[{"exclusiveMinimum":0,"maximum":60,"type":"number"},{"type":"null"}],"default":null,"description":"Bin width in days; omit to get about 150 points","title":"Bin Days"},"latitude":{"anyOf":[{"maximum":90,"minimum":-90,"type":"number"},{"type":"null"}],"default":null,"description":"Observer latitude in degrees (north positive). Omit to use place or the saved default.","title":"Latitude"},"longitude":{"anyOf":[{"maximum":180,"minimum":-180,"type":"number"},{"type":"null"}],"default":null,"description":"Observer longitude in degrees (east positive). Omit to use place or the saved default.","title":"Longitude"},"place":{"anyOf":[{"type":"string"},{"type":"null"}],"default":null,"description":"Place name to observe from instead of coordinates, e.g. 'Moab, Utah'.","title":"Place"}},"required":["name"],"type":"object","title":"get_light_curveArguments"},"name":"get_light_curve","outputSchema":{"type":"object","additionalProperties":true,"title":"get_light_curveDictOutput"}},{"annotations":{"idempotentHint":true,"openWorldHint":true,"readOnlyHint":true},"description":"Supernovae currently bright enough for amateur telescopes, brightest first.\n\nUse for 'any bright supernovae right now', 'is there a supernova in M101' or 'what can I\nimage tonight'. Gives type, host galaxy, position, latest and peak magnitude with dates,\ndiscovery date and discoverer, and with a location the best time tonight.\n","inputSchema":{"properties":{"max_magnitude":{"default":16.0,"description":"Only supernovae at least this bright","maximum":17,"minimum":8,"title":"Max Magnitude","type":"number"},"limit":{"default":15,"description":"Maximum supernovae","maximum":50,"minimum":1,"title":"Limit","type":"integer"},"include_candidates":{"default":false,"description":"Also list unconfirmed supernova candidates found by the ALeRCE broker in ZTF data (mostly fainter than 17)","title":"Include Candidates","type":"boolean"},"candidate_days":{"default":10,"description":"With candidates: first detected within this many days","maximum":60,"minimum":1,"title":"Candidate Days","type":"integer"},"min_altitude":{"default":20.0,"description":"Minimum useful altitude in degrees","maximum":80,"minimum":0,"title":"Min Altitude","type":"number"},"date":{"anyOf":[{"type":"string"},{"type":"null"}],"default":null,"description":"Local date (YYYY-MM-DD) whose evening starts the night. Omit for tonight.","title":"Date"},"latitude":{"anyOf":[{"maximum":90,"minimum":-90,"type":"number"},{"type":"null"}],"default":null,"description":"Observer latitude in degrees (north positive). Omit to use place or the saved default.","title":"Latitude"},"longitude":{"anyOf":[{"maximum":180,"minimum":-180,"type":"number"},{"type":"null"}],"default":null,"description":"Observer longitude in degrees (east positive). Omit to use place or the saved default.","title":"Longitude"},"place":{"anyOf":[{"type":"string"},{"type":"null"}],"default":null,"description":"Place name to observe from instead of coordinates, e.g. 'Moab, Utah'.","title":"Place"}},"type":"object","title":"get_recent_supernovaeArguments"},"name":"get_recent_supernovae","outputSchema":{"type":"object","additionalProperties":true,"title":"get_recent_supernovaeDictOutput"}},{"annotations":{"idempotentHint":true,"openWorldHint":true,"readOnlyHint":true},"description":"Recent novae in our Galaxy, with peak and current brightness, newest first.\n\nUse for 'is there a nova visible now' or 'how bright is Nova Sagittae'. Lists novae from\nKoji Mukai's list with discovery date, peak magnitude, the latest AAVSO magnitude and with a\nlocation whether it is up tonight.\n","inputSchema":{"properties":{"days":{"default":120,"description":"Discovered within this many days","maximum":730,"minimum":1,"title":"Days","type":"integer"},"include_extragalactic":{"default":false,"description":"Also list novae in other galaxies, mostly M31 (magnitude 15-19)","title":"Include Extragalactic","type":"boolean"},"min_altitude":{"default":15.0,"description":"Minimum useful altitude in degrees","maximum":80,"minimum":0,"title":"Min Altitude","type":"number"},"date":{"anyOf":[{"type":"string"},{"type":"null"}],"default":null,"description":"Local date (YYYY-MM-DD) whose evening starts the night. Omit for tonight.","title":"Date"},"latitude":{"anyOf":[{"maximum":90,"minimum":-90,"type":"number"},{"type":"null"}],"default":null,"description":"Observer latitude in degrees (north positive). Omit to use place or the saved default.","title":"Latitude"},"longitude":{"anyOf":[{"maximum":180,"minimum":-180,"type":"number"},{"type":"null"}],"default":null,"description":"Observer longitude in degrees (east positive). Omit to use place or the saved default.","title":"Longitude"},"place":{"anyOf":[{"type":"string"},{"type":"null"}],"default":null,"description":"Place name to observe from instead of coordinates, e.g. 'Moab, Utah'.","title":"Place"}},"type":"object","title":"get_novaeArguments"},"name":"get_novae","outputSchema":{"type":"object","additionalProperties":true,"title":"get_novaeDictOutput"}},{"annotations":{"idempotentHint":true,"openWorldHint":true,"readOnlyHint":true},"description":"Which spacecraft NASA's Deep Space Network is talking to right now.\n\nUse for 'is anyone talking to Voyager', 'what is the DSN doing' or 'how far away is Juno'.\nLists each spacecraft in contact, the antennas, distance and light time, and whether data\nor commands are flowing. Live from DSN Now; contacts change every few hours.\n","inputSchema":{"properties":{"spacecraft":{"anyOf":[{"type":"string"},{"type":"null"}],"default":null,"description":"Only contacts with this spacecraft, e.g. 'Voyager', 'JWST', 'Juno'","title":"Spacecraft"},"include_antennas":{"default":false,"description":"Also list every antenna at Goldstone, Madrid and Canberra with its activity and pointing","title":"Include Antennas","type":"boolean"}},"type":"object","title":"get_dsn_statusArguments"},"name":"get_dsn_status","outputSchema":{"type":"object","additionalProperties":true,"title":"get_dsn_statusDictOutput"}},{"annotations":{"idempotentHint":true,"openWorldHint":true,"readOnlyHint":true},"description":"Facts about a known exoplanet, or all planets of a host star, from the NASA Exoplanet Archive.\n\nUse for 'tell me about TRAPPIST-1 e', 'how big is HD 209458 b' or 'what planets orbit\nKepler-90'. Gives discovery, orbit, radius, mass, temperature, insolation, the host star and\nits distance; for transiting planets, the next few transit times with their uncertainty.\n","inputSchema":{"properties":{"name":{"description":"Planet name ('TRAPPIST-1 e', 'HD 189733 b') or host star name to list its planets ('TRAPPIST-1', 'Kepler-22')","title":"Name","type":"string"},"latitude":{"anyOf":[{"maximum":90,"minimum":-90,"type":"number"},{"type":"null"}],"default":null,"description":"Observer latitude in degrees (north positive). Omit to use place or the saved default.","title":"Latitude"},"longitude":{"anyOf":[{"maximum":180,"minimum":-180,"type":"number"},{"type":"null"}],"default":null,"description":"Observer longitude in degrees (east positive). Omit to use place or the saved default.","title":"Longitude"},"place":{"anyOf":[{"type":"string"},{"type":"null"}],"default":null,"description":"Place name to observe from instead of coordinates, e.g. 'Moab, Utah'.","title":"Place"}},"required":["name"],"type":"object","title":"get_exoplanetArguments"},"name":"get_exoplanet","outputSchema":{"type":"object","additionalProperties":true,"title":"get_exoplanetDictOutput"}},{"annotations":{"idempotentHint":true,"openWorldHint":true,"readOnlyHint":true},"description":"Find exoplanets by size, distance, starlight received, discovery method or year.\n\nUse for 'nearest Earth-sized planets', 'planets in the habitable zone within 50 light years'\nor 'exoplanets found by direct imaging'. Returns the total number of matches and the top\nresults with radius, mass, temperature, insolation and distance.\n","inputSchema":{"properties":{"discovery_method":{"anyOf":[{"type":"string"},{"type":"null"}],"default":null,"description":"e.g. 'Transit', 'Radial Velocity', 'Imaging', 'Microlensing'","title":"Discovery Method"},"min_radius_earth":{"anyOf":[{"exclusiveMinimum":0,"type":"number"},{"type":"null"}],"default":null,"description":"Smallest planet radius, Earth radii","title":"Min Radius Earth"},"max_radius_earth":{"anyOf":[{"exclusiveMinimum":0,"type":"number"},{"type":"null"}],"default":null,"description":"Largest planet radius, Earth radii","title":"Max Radius Earth"},"max_distance_pc":{"anyOf":[{"exclusiveMinimum":0,"type":"number"},{"type":"null"}],"default":null,"description":"Only systems within this distance (1 pc = 3.26 light years)","title":"Max Distance Pc"},"min_insolation":{"anyOf":[{"minimum":0,"type":"number"},{"type":"null"}],"default":null,"description":"Least starlight received, relative to Earth (Earth = 1)","title":"Min Insolation"},"max_insolation":{"anyOf":[{"minimum":0,"type":"number"},{"type":"null"}],"default":null,"description":"Most starlight received, relative to Earth; about 0.35-1.75 is a rough habitable range","title":"Max Insolation"},"max_host_magnitude":{"anyOf":[{"type":"number"},{"type":"null"}],"default":null,"description":"Only host stars at least this bright (V)","title":"Max Host Magnitude"},"transiting_only":{"default":false,"description":"Only planets seen to transit their star","title":"Transiting Only","type":"boolean"},"discovered_since":{"anyOf":[{"maximum":2100,"minimum":1989,"type":"integer"},{"type":"null"}],"default":null,"description":"Discovered in or after this year","title":"Discovered Since"},"sort_by":{"default":"distance","description":"Order of results","enum":["distance","radius","mass","newest","host_brightness","period"],"title":"Sort By","type":"string"},"limit":{"default":20,"description":"Maximum planets","maximum":100,"minimum":1,"title":"Limit","type":"integer"}},"type":"object","title":"search_exoplanetsArguments"},"name":"search_exoplanets","outputSchema":{"type":"object","additionalProperties":true,"title":"search_exoplanetsDictOutput"}},{"annotations":{"idempotentHint":true,"openWorldHint":true,"readOnlyHint":true},"description":"Exoplanet transits observable from the location tonight, in time order.\n\nUse for 'which exoplanet transits can I record tonight' or planning transit photometry.\nGives ingress, mid-transit and egress in local time (converted from the archive's barycentric\nephemeris), depth in percent and millimagnitudes, the host star's brightness, altitudes during\nthe transit, and the timing uncertainty from the ephemeris.\n","inputSchema":{"properties":{"max_host_magnitude":{"default":12.0,"description":"Only host stars at least this bright (V)","maximum":13,"minimum":5,"title":"Max Host Magnitude","type":"number"},"min_depth_percent":{"default":0.5,"description":"Shallowest transit worth trying (1% = about 11 mmag); 0.5% suits most amateur setups","maximum":5,"minimum":0.05,"title":"Min Depth Percent","type":"number"},"min_altitude":{"default":30.0,"description":"Minimum useful altitude in degrees","maximum":80,"minimum":0,"title":"Min Altitude","type":"number"},"full_transits_only":{"default":true,"description":"Only transits whose ingress and egress both fall in the dark window","title":"Full Transits Only","type":"boolean"},"max_timing_uncertainty_min":{"default":30,"description":"Skip planets whose predicted time is less certain than this","exclusiveMinimum":0,"maximum":600,"title":"Max Timing Uncertainty Min","type":"number"},"date":{"anyOf":[{"type":"string"},{"type":"null"}],"default":null,"description":"Local date (YYYY-MM-DD) whose evening starts the night. Omit for tonight.","title":"Date"},"latitude":{"anyOf":[{"maximum":90,"minimum":-90,"type":"number"},{"type":"null"}],"default":null,"description":"Observer latitude in degrees (north positive). Omit to use place or the saved default.","title":"Latitude"},"longitude":{"anyOf":[{"maximum":180,"minimum":-180,"type":"number"},{"type":"null"}],"default":null,"description":"Observer longitude in degrees (east positive). Omit to use place or the saved default.","title":"Longitude"},"place":{"anyOf":[{"type":"string"},{"type":"null"}],"default":null,"description":"Place name to observe from instead of coordinates, e.g. 'Moab, Utah'.","title":"Place"},"limit":{"default":20,"description":"Maximum transits","maximum":50,"minimum":1,"title":"Limit","type":"integer"}},"type":"object","title":"get_transits_tonightArguments"},"name":"get_transits_tonight","outputSchema":{"type":"object","additionalProperties":true,"title":"get_transits_tonightDictOutput"}},{"annotations":{"idempotentHint":true,"openWorldHint":true,"readOnlyHint":true},"description":"Gravitational-wave detections: recent public alerts, or confirmed events from the catalog.\n\nUse for 'any recent gravitational wave detections', 'tell me about GW170817' or 'the most\nmassive black hole merger detected'. Alerts give time, false-alarm rate, detectors and the\nsource classification (binary black hole, neutron stars, noise); catalog events give masses,\nfinal mass, distance and signal-to-noise with uncertainties.\n","inputSchema":{"properties":{"event":{"anyOf":[{"type":"string"},{"type":"null"}],"default":null,"description":"An event: a catalog name ('GW150914', 'GW170817') or a public alert id ('S251117dq')","title":"Event"},"source":{"default":"alerts","description":"'alerts': latest significant public alerts (GraceDB); 'catalog': confirmed events with masses and distances (GWOSC)","enum":["alerts","catalog"],"title":"Source","type":"string"},"sort_by":{"default":"date","description":"Catalog order: newest, farthest, most massive, or loudest","enum":["date","distance","mass","snr"],"title":"Sort By","type":"string"},"limit":{"default":10,"description":"Maximum events","maximum":50,"minimum":1,"title":"Limit","type":"integer"},"include_retracted":{"default":false,"description":"Alerts: also list alerts later retracted","title":"Include Retracted","type":"boolean"},"min_probability":{"default":0.5,"description":"Catalog: lowest probability of being astrophysical","maximum":1,"minimum":0,"title":"Min Probability","type":"number"}},"type":"object","title":"get_gravitational_wave_eventsArguments"},"name":"get_gravitational_wave_events","outputSchema":{"type":"object","additionalProperties":true,"title":"get_gravitational_wave_eventsDictOutput"}},{"annotations":{"idempotentHint":true,"openWorldHint":true,"readOnlyHint":true},"description":"Field of view and image scale for a camera on a telescope or lens, and/or an eyepiece's view.\n\nUse for 'what field does my ASI2600 give on an 80 mm f/6', 'am I oversampled' or 'what\nmagnification and true field does a 25 mm eyepiece give'. Camera: field in arcminutes and\ndegrees, arcseconds per pixel and how that matches the seeing. Eyepiece: magnification, true\nfield and exit pupil.\n","inputSchema":{"properties":{"focal_length_mm":{"description":"Focal length in mm (telescope or lens), before any Barlow or reducer","exclusiveMinimum":0,"maximum":20000,"title":"Focal Length Mm","type":"number"},"aperture_mm":{"anyOf":[{"exclusiveMinimum":0,"maximum":2000,"type":"number"},{"type":"null"}],"default":null,"description":"Aperture in mm, for focal ratio, exit pupil and resolution","title":"Aperture Mm"},"sensor":{"anyOf":[{"type":"string"},{"type":"null"}],"default":null,"description":"Sensor preset: full_frame, aps_c_canon, aps_c, micro_four_thirds, asi6200, asi2600, asi533, asi294, asi183, asi585, asi462, asi120","title":"Sensor"},"sensor_width_mm":{"anyOf":[{"exclusiveMinimum":0,"maximum":100,"type":"number"},{"type":"null"}],"default":null,"description":"Sensor width in mm, if not using a preset","title":"Sensor Width Mm"},"sensor_height_mm":{"anyOf":[{"exclusiveMinimum":0,"maximum":100,"type":"number"},{"type":"null"}],"default":null,"description":"Sensor height in mm, if not using a preset","title":"Sensor Height Mm"},"pixel_um":{"anyOf":[{"exclusiveMinimum":0,"maximum":30,"type":"number"},{"type":"null"}],"default":null,"description":"Pixel size in micrometres","title":"Pixel Um"},"megapixels":{"anyOf":[{"exclusiveMinimum":0,"maximum":200,"type":"number"},{"type":"null"}],"default":null,"description":"Sensor megapixels, to work out pixel size","title":"Megapixels"},"multiplier":{"default":1.0,"description":"Barlow (e.g. 2) or reducer (e.g. 0.8) factor","exclusiveMinimum":0.2,"maximum":6,"title":"Multiplier","type":"number"},"seeing_arcsec":{"default":2.0,"description":"Typical seeing (star blur) in arcseconds: 1 excellent, 2 average, 3-4 poor","maximum":6,"minimum":0.3,"title":"Seeing Arcsec","type":"number"},"eyepiece_mm":{"anyOf":[{"exclusiveMinimum":0,"maximum":100,"type":"number"},{"type":"null"}],"default":null,"description":"Eyepiece focal length in mm, for the visual view","title":"Eyepiece Mm"},"eyepiece_afov_deg":{"anyOf":[{"exclusiveMinimum":20,"maximum":120,"type":"number"},{"type":"null"}],"default":null,"description":"Eyepiece apparent field in degrees (52 for a Plössl if omitted)","title":"Eyepiece Afov Deg"}},"required":["focal_length_mm"],"type":"object","title":"calculate_field_of_viewArguments"},"name":"calculate_field_of_view","outputSchema":{"type":"object","additionalProperties":true,"title":"calculate_field_of_viewDictOutput"}},{"annotations":{"idempotentHint":true,"openWorldHint":true,"readOnlyHint":true},"description":"Whether a target fits a camera's field, how much it fills, and which way to rotate the camera.\n\nUse for 'will M31 fit with my 400 mm and APS-C camera' or 'what focal length for the Moon'.\nUses catalogued sizes and orientations (OpenNGC) or a planet's current apparent size, and\nsuggests a focal length or a mosaic when the fit is poor.\n","inputSchema":{"properties":{"target":{"description":"Object to frame: 'M31', 'North America Nebula', 'Moon', 'Jupiter'","title":"Target","type":"string"},"focal_length_mm":{"description":"Focal length in mm (telescope or lens), before any Barlow or reducer","exclusiveMinimum":0,"maximum":20000,"title":"Focal Length Mm","type":"number"},"sensor":{"anyOf":[{"type":"string"},{"type":"null"}],"default":null,"description":"Sensor preset: full_frame, aps_c_canon, aps_c, micro_four_thirds, asi6200, asi2600, asi533, asi294, asi183, asi585, asi462, asi120","title":"Sensor"},"sensor_width_mm":{"anyOf":[{"exclusiveMinimum":0,"maximum":100,"type":"number"},{"type":"null"}],"default":null,"description":"Sensor width in mm, if not using a preset","title":"Sensor Width Mm"},"sensor_height_mm":{"anyOf":[{"exclusiveMinimum":0,"maximum":100,"type":"number"},{"type":"null"}],"default":null,"description":"Sensor height in mm, if not using a preset","title":"Sensor Height Mm"},"multiplier":{"default":1.0,"description":"Barlow (e.g. 2) or reducer (e.g. 0.8) factor","exclusiveMinimum":0.2,"maximum":6,"title":"Multiplier","type":"number"}},"required":["target","focal_length_mm"],"type":"object","title":"frame_targetArguments"},"name":"frame_target","outputSchema":{"type":"object","additionalProperties":true,"title":"frame_targetDictOutput"}},{"annotations":{"idempotentHint":true,"openWorldHint":true,"readOnlyHint":true},"description":"A mosaic plan: how many panels, and the RA/Dec centre of each, to cover a large target.\n\nUse for 'how many panels to cover the Veil Nebula with my 600 mm' or to get panel\ncoordinates for a sequencer. Lays a grid of camera fields with the requested overlap,\nrotated along the target's long axis.\n","inputSchema":{"properties":{"focal_length_mm":{"description":"Focal length in mm (telescope or lens), before any Barlow or reducer","exclusiveMinimum":0,"maximum":20000,"title":"Focal Length Mm","type":"number"},"target":{"anyOf":[{"type":"string"},{"type":"null"}],"default":null,"description":"Object to cover; or give ra_deg, dec_deg, width_arcmin and height_arcmin","title":"Target"},"ra_deg":{"anyOf":[{"exclusiveMaximum":360,"minimum":0,"type":"number"},{"type":"null"}],"default":null,"description":"Centre right ascension (J2000 degrees)","title":"Ra Deg"},"dec_deg":{"anyOf":[{"maximum":90,"minimum":-90,"type":"number"},{"type":"null"}],"default":null,"description":"Centre declination (J2000 degrees)","title":"Dec Deg"},"width_arcmin":{"anyOf":[{"exclusiveMinimum":0,"maximum":3600,"type":"number"},{"type":"null"}],"default":null,"description":"Area to cover, along the width axis","title":"Width Arcmin"},"height_arcmin":{"anyOf":[{"exclusiveMinimum":0,"maximum":3600,"type":"number"},{"type":"null"}],"default":null,"description":"Area to cover, across the width axis","title":"Height Arcmin"},"angle_deg":{"anyOf":[{"exclusiveMaximum":360,"minimum":0,"type":"number"},{"type":"null"}],"default":null,"description":"Position angle of the mosaic's width axis, east of north; defaults to the target's major axis, else 90 (east-west)","title":"Angle Deg"},"overlap_percent":{"default":15,"description":"Overlap between neighbouring panels","maximum":50,"minimum":0,"title":"Overlap Percent","type":"number"},"sensor":{"anyOf":[{"type":"string"},{"type":"null"}],"default":null,"description":"Sensor preset: full_frame, aps_c_canon, aps_c, micro_four_thirds, asi6200, asi2600, asi533, asi294, asi183, asi585, asi462, asi120","title":"Sensor"},"sensor_width_mm":{"anyOf":[{"exclusiveMinimum":0,"maximum":100,"type":"number"},{"type":"null"}],"default":null,"description":"Sensor width in mm, if not using a preset","title":"Sensor Width Mm"},"sensor_height_mm":{"anyOf":[{"exclusiveMinimum":0,"maximum":100,"type":"number"},{"type":"null"}],"default":null,"description":"Sensor height in mm, if not using a preset","title":"Sensor Height Mm"},"multiplier":{"default":1.0,"description":"Barlow (e.g. 2) or reducer (e.g. 0.8) factor","exclusiveMinimum":0.2,"maximum":6,"title":"Multiplier","type":"number"}},"required":["focal_length_mm"],"type":"object","title":"plan_mosaicArguments"},"name":"plan_mosaic","outputSchema":{"type":"object","additionalProperties":true,"title":"plan_mosaicDictOutput"}},{"annotations":{"idempotentHint":true,"openWorldHint":true,"readOnlyHint":true},"description":"Longest untracked exposure before stars trail, by the NPF rule (and the older 500 rule).\n\nUse for 'how long can I expose the Milky Way at 14 mm f/2.8 on my camera'. Needs the pixel\nsize (directly, from a sensor preset, or from sensor size and megapixels). Aiming away from\nthe celestial equator allows longer exposures; give a target or declination to include that.\n","inputSchema":{"properties":{"focal_length_mm":{"description":"Lens focal length in mm (actual, not 35 mm equivalent)","exclusiveMinimum":0,"maximum":2000,"title":"Focal Length Mm","type":"number"},"f_number":{"description":"Aperture as an f-number, e.g. 2.8","exclusiveMinimum":0.7,"maximum":32,"title":"F Number","type":"number"},"sensor":{"anyOf":[{"type":"string"},{"type":"null"}],"default":null,"description":"Sensor preset: full_frame, aps_c_canon, aps_c, micro_four_thirds, asi6200, asi2600, asi533, asi294, asi183, asi585, asi462, asi120","title":"Sensor"},"sensor_width_mm":{"anyOf":[{"exclusiveMinimum":0,"maximum":100,"type":"number"},{"type":"null"}],"default":null,"description":"Sensor width in mm, if not using a preset","title":"Sensor Width Mm"},"sensor_height_mm":{"anyOf":[{"exclusiveMinimum":0,"maximum":100,"type":"number"},{"type":"null"}],"default":null,"description":"Sensor height in mm, if not using a preset","title":"Sensor Height Mm"},"pixel_um":{"anyOf":[{"exclusiveMinimum":0,"maximum":30,"type":"number"},{"type":"null"}],"default":null,"description":"Pixel size in micrometres","title":"Pixel Um"},"megapixels":{"anyOf":[{"exclusiveMinimum":0,"maximum":200,"type":"number"},{"type":"null"}],"default":null,"description":"Sensor megapixels, to work out pixel size","title":"Megapixels"},"crop_factor":{"anyOf":[{"exclusiveMinimum":0.3,"maximum":10,"type":"number"},{"type":"null"}],"default":null,"description":"Crop factor for the 500 rule; worked out from the sensor if omitted","title":"Crop Factor"},"target":{"anyOf":[{"type":"string"},{"type":"null"}],"default":null,"description":"Aim point, for its declination: 'Milky Way core', 'Polaris', 'M31'","title":"Target"},"declination_deg":{"anyOf":[{"maximum":90,"minimum":-90,"type":"number"},{"type":"null"}],"default":null,"description":"Declination of the aim point, instead of a target","title":"Declination Deg"}},"required":["focal_length_mm","f_number"],"type":"object","title":"calculate_exposureArguments"},"name":"calculate_exposure","outputSchema":{"type":"object","additionalProperties":true,"title":"calculate_exposureDictOutput"}},{"annotations":{"idempotentHint":true,"openWorldHint":true,"readOnlyHint":true},"description":"When and where to photograph the Milky Way's core: dark, moonless windows with the galactic centre up.\n\nUse for 'can I shoot the Milky Way core tonight', 'best nights this month for Milky Way photos'\nor 'when does Milky Way season start here'. Gives the shooting window, the core's altitude and\ncompass direction at its start, best moment and end, how steeply the band is tilted (portrait\nframe or panorama), the Moon, and the season month by month. Does not check clouds (use\nget_sky_forecast); for exposure length use calculate_exposure with target 'Milky Way core'.\n","inputSchema":{"properties":{"date":{"anyOf":[{"type":"string"},{"type":"null"}],"default":null,"description":"Local date (YYYY-MM-DD) whose evening starts the night. Omit for tonight.","title":"Date"},"days":{"default":1,"description":"Nights to plan, starting with date; more than one ranks them","maximum":60,"minimum":1,"title":"Days","type":"integer"},"min_altitude":{"default":10.0,"description":"Lowest useful altitude of the core in degrees","maximum":60,"minimum":0,"title":"Min Altitude","type":"number"},"terrain":{"default":true,"description":"Account for hills and mountains on the local horizon (first use per location takes a few seconds)","title":"Terrain","type":"boolean"},"latitude":{"anyOf":[{"maximum":90,"minimum":-90,"type":"number"},{"type":"null"}],"default":null,"description":"Observer latitude in degrees (north positive). Omit to use place or the saved default.","title":"Latitude"},"longitude":{"anyOf":[{"maximum":180,"minimum":-180,"type":"number"},{"type":"null"}],"default":null,"description":"Observer longitude in degrees (east positive). Omit to use place or the saved default.","title":"Longitude"},"place":{"anyOf":[{"type":"string"},{"type":"null"}],"default":null,"description":"Place name to observe from instead of coordinates, e.g. 'Moab, Utah'.","title":"Place"}},"type":"object","title":"plan_milky_way_shotArguments"},"name":"plan_milky_way_shot","outputSchema":{"type":"object","additionalProperties":true,"title":"plan_milky_way_shotDictOutput"}},{"annotations":{"idempotentHint":true,"openWorldHint":true,"readOnlyHint":true},"description":"A survey image of any patch of sky, from DSS, Pan-STARRS, SDSS, Legacy Surveys, 2MASS, WISE and others.\n\nUse for 'show me what M51 looks like', 'get a DSS image of these coordinates' or a reference\nframe to compare with your own photo (spotting a new star, checking framing). North up, east\nleft. The image is shown and saved under ~/.astronomy-mcp/images.\n","inputSchema":{"properties":{"target":{"anyOf":[{"type":"string"},{"type":"null"}],"default":null,"description":"Object to centre on: 'M51', 'Stephan's Quintet', 'Uranus'; or give ra_deg and dec_deg","title":"Target"},"ra_deg":{"anyOf":[{"exclusiveMaximum":360,"minimum":0,"type":"number"},{"type":"null"}],"default":null,"description":"Centre right ascension (J2000 degrees), instead of a target","title":"Ra Deg"},"dec_deg":{"anyOf":[{"maximum":90,"minimum":-90,"type":"number"},{"type":"null"}],"default":null,"description":"Centre declination (J2000 degrees), instead of a target","title":"Dec Deg"},"fov_deg":{"anyOf":[{"exclusiveMinimum":0.005,"maximum":30,"type":"number"},{"type":"null"}],"default":null,"description":"Width of the field in degrees. Defaults to 1.5x the target's catalogued size, else 0.5","title":"Fov Deg"},"survey":{"default":"auto","description":"Image source. 'auto': DSS2 (whole sky) up to 5°, the Mellinger photographic mosaic for wider fields. Pan-STARRS is sharper but only north of -30°; 2MASS and WISE are infrared.","enum":["auto","dss2_color","dss2_red","dss2_blue","panstarrs_color","panstarrs_g","panstarrs_r","sdss_color","legacy_color","2mass_color","wise_color","mellinger_color"],"title":"Survey","type":"string"},"width_px":{"default":800,"description":"Image width in pixels","maximum":3000,"minimum":64,"title":"Width Px","type":"integer"},"height_px":{"anyOf":[{"maximum":3000,"minimum":64,"type":"integer"},{"type":"null"}],"default":null,"description":"Image height in pixels; defaults to width_px","title":"Height Px"},"image_format":{"default":"jpg","description":"'fits' keeps the data and a WCS header; it is saved, not shown","enum":["jpg","png","fits"],"title":"Image Format","type":"string"},"time":{"anyOf":[{"type":"string"},{"type":"null"}],"default":null,"description":"For a planet: ISO 8601 time to place it at (naive = the saved location's local time). Omit for now.","title":"Time"}},"type":"object","title":"get_survey_cutoutArguments"},"name":"get_survey_cutout"},{"annotations":{"idempotentHint":true,"openWorldHint":true,"readOnlyHint":true},"description":"A finder chart: a survey image with the target marked, your camera frame or eyepiece field, Telrad rings,\nnearby objects labelled, compass and scale bar, flipped to match what your telescope shows.\n\nUse for 'make me a finder chart for M97', 'how do I find NGC 891 with my Telrad', 'show my\ncamera's framing on M31' or 'where is Neptune among the stars'. Shown and saved as a PNG under\n~/.astronomy-mcp/charts for printing.\n","inputSchema":{"properties":{"target":{"anyOf":[{"type":"string"},{"type":"null"}],"default":null,"description":"Object to find: 'M97', 'NGC 891', 'Neptune'; or give ra_deg and dec_deg","title":"Target"},"ra_deg":{"anyOf":[{"exclusiveMaximum":360,"minimum":0,"type":"number"},{"type":"null"}],"default":null,"description":"Centre right ascension (J2000 degrees), instead of a target","title":"Ra Deg"},"dec_deg":{"anyOf":[{"maximum":90,"minimum":-90,"type":"number"},{"type":"null"}],"default":null,"description":"Centre declination (J2000 degrees), instead of a target","title":"Dec Deg"},"fov_deg":{"anyOf":[{"maximum":30,"minimum":0.05,"type":"number"},{"type":"null"}],"default":null,"description":"Chart width in degrees. Defaults to twice the camera frame, 2.5x the eyepiece field, 9° with Telrad rings, else from the target's size","title":"Fov Deg"},"focal_length_mm":{"anyOf":[{"exclusiveMinimum":0,"maximum":20000,"type":"number"},{"type":"null"}],"default":null,"description":"Telescope or lens focal length, to draw the camera frame and/or eyepiece field","title":"Focal Length Mm"},"sensor":{"anyOf":[{"type":"string"},{"type":"null"}],"default":null,"description":"Sensor preset: full_frame, aps_c_canon, aps_c, micro_four_thirds, asi6200, asi2600, asi533, asi294, asi183, asi585, asi462, asi120","title":"Sensor"},"sensor_width_mm":{"anyOf":[{"exclusiveMinimum":0,"maximum":100,"type":"number"},{"type":"null"}],"default":null,"description":"Sensor width in mm, if not using a preset","title":"Sensor Width Mm"},"sensor_height_mm":{"anyOf":[{"exclusiveMinimum":0,"maximum":100,"type":"number"},{"type":"null"}],"default":null,"description":"Sensor height in mm, if not using a preset","title":"Sensor Height Mm"},"rotation_deg":{"anyOf":[{"exclusiveMaximum":360,"minimum":0,"type":"number"},{"type":"null"}],"default":null,"description":"Camera angle: position angle of the sensor's long side, east of north. Defaults to the target's long axis, else 90 (east-west)","title":"Rotation Deg"},"eyepiece_mm":{"anyOf":[{"exclusiveMinimum":0,"maximum":100,"type":"number"},{"type":"null"}],"default":null,"description":"Eyepiece focal length in mm, to draw its true field","title":"Eyepiece Mm"},"eyepiece_afov_deg":{"anyOf":[{"exclusiveMinimum":20,"maximum":120,"type":"number"},{"type":"null"}],"default":null,"description":"Eyepiece apparent field in degrees (52 if omitted)","title":"Eyepiece Afov Deg"},"multiplier":{"default":1.0,"description":"Barlow (e.g. 2) or reducer (e.g. 0.8) factor","exclusiveMinimum":0.2,"maximum":6,"title":"Multiplier","type":"number"},"telrad":{"default":false,"description":"Draw Telrad rings (0.5°, 2° and 4°) around the target","title":"Telrad","type":"boolean"},"orientation":{"default":"north_up","description":"'north_up' for naked eye, binoculars and correct-image finders; 'mirrored' for a star diagonal; 'rotated' (180°) for a Newtonian or straight-through finder","enum":["north_up","mirrored","rotated"],"title":"Orientation","type":"string"},"style":{"default":"print","description":"'print': black stars on white; 'photo': the survey image as it is","enum":["print","photo"],"title":"Style","type":"string"},"survey":{"default":"auto","description":"Image source. 'auto': DSS2 (whole sky) up to 5°, the Mellinger photographic mosaic for wider fields. Pan-STARRS is sharper but only north of -30°; 2MASS and WISE are infrared.","enum":["auto","dss2_color","dss2_red","dss2_blue","panstarrs_color","panstarrs_g","panstarrs_r","sdss_color","legacy_color","2mass_color","wise_color","mellinger_color"],"title":"Survey","type":"string"},"label_objects":{"default":true,"description":"Mark and name other NGC/IC/Messier objects in the field","title":"Label Objects","type":"boolean"},"size_px":{"default":900,"description":"Chart width in pixels","maximum":2000,"minimum":400,"title":"Size Px","type":"integer"},"time":{"anyOf":[{"type":"string"},{"type":"null"}],"default":null,"description":"For a planet: ISO 8601 time to place it at (naive = the saved location's local time). Omit for now.","title":"Time"}},"type":"object","title":"generate_finder_chartArguments"},"name":"generate_finder_chart"},{"annotations":{"destructiveHint":false,"idempotentHint":false,"openWorldHint":true,"readOnlyHint":false},"description":"Plate-solve an astrophoto with Astrometry.net: exact centre, field size, pixel scale, camera angle and named objects.\n\nUse for 'what is in this photo', 'where was my camera pointed' or 'what are my image scale\nand camera rotation'. Uploads the image to nova.astrometry.net (marked private) and needs a\nfree API key in the ASTROMETRY_NET_API_KEY environment variable. Solving takes one to several\nminutes; if it isn't done within wait_seconds, call again with the returned submission_id.\nFocal length and sensor, or a rough target, speed it up. Export camera raw files to JPEG,\nTIFF or FITS first.\n","inputSchema":{"properties":{"image":{"anyOf":[{"type":"string"},{"type":"null"}],"default":null,"description":"Local path to a JPEG, PNG, TIFF or FITS file, or an http(s) URL of one","title":"Image"},"submission_id":{"anyOf":[{"minimum":1,"type":"integer"},{"type":"null"}],"default":null,"description":"Check on an earlier submission instead of uploading","title":"Submission Id"},"wait_seconds":{"default":60,"description":"How long to wait for the solve before handing back the submission id","maximum":600,"minimum":0,"title":"Wait Seconds","type":"integer"},"target":{"anyOf":[{"type":"string"},{"type":"null"}],"default":null,"description":"Roughly where the image points, to speed up the solve: 'M31', 'Vega'","title":"Target"},"ra_deg":{"anyOf":[{"exclusiveMaximum":360,"minimum":0,"type":"number"},{"type":"null"}],"default":null,"description":"Approximate centre RA (J2000 degrees), instead of a target","title":"Ra Deg"},"dec_deg":{"anyOf":[{"maximum":90,"minimum":-90,"type":"number"},{"type":"null"}],"default":null,"description":"Approximate centre declination (J2000 degrees)","title":"Dec Deg"},"search_radius_deg":{"default":10.0,"description":"How far from the target or RA/Dec to search","exclusiveMinimum":0,"maximum":180,"title":"Search Radius Deg","type":"number"},"arcsec_per_pixel":{"anyOf":[{"exclusiveMinimum":0.01,"maximum":3600,"type":"number"},{"type":"null"}],"default":null,"description":"Image scale, if known","title":"Arcsec Per Pixel"},"focal_length_mm":{"anyOf":[{"exclusiveMinimum":0,"maximum":20000,"type":"number"},{"type":"null"}],"default":null,"description":"Focal length used, including any reducer or Barlow, for a scale hint","title":"Focal Length Mm"},"sensor":{"anyOf":[{"type":"string"},{"type":"null"}],"default":null,"description":"Sensor preset: full_frame, aps_c_canon, aps_c, micro_four_thirds, asi6200, asi2600, asi533, asi294, asi183, asi585, asi462, asi120","title":"Sensor"},"sensor_width_mm":{"anyOf":[{"exclusiveMinimum":0,"maximum":100,"type":"number"},{"type":"null"}],"default":null,"description":"Sensor width in mm, if not using a preset","title":"Sensor Width Mm"},"sensor_height_mm":{"anyOf":[{"exclusiveMinimum":0,"maximum":100,"type":"number"},{"type":"null"}],"default":null,"description":"Sensor height in mm, if not using a preset","title":"Sensor Height Mm"},"pixel_um":{"anyOf":[{"exclusiveMinimum":0,"maximum":30,"type":"number"},{"type":"null"}],"default":null,"description":"Pixel size in micrometres","title":"Pixel Um"}},"type":"object","title":"plate_solve_imageArguments"},"name":"plate_solve_image","outputSchema":{"type":"object","additionalProperties":true,"title":"plate_solve_imageDictOutput"}},{"annotations":{"idempotentHint":true,"openWorldHint":true,"readOnlyHint":true},"description":"Aurora chances and geomagnetic storm levels, now and for the next 3 days (NOAA SWPC).\n\nUse for 'will I see the northern lights', 'is there a geomagnetic storm' or 'what's the Kp'.\nWith a location, adds the current aurora probability overhead and toward the pole.\n","inputSchema":{"properties":{"latitude":{"anyOf":[{"maximum":90,"minimum":-90,"type":"number"},{"type":"null"}],"default":null,"description":"Observer latitude in degrees (north positive). Omit to use place or the saved default.","title":"Latitude"},"longitude":{"anyOf":[{"maximum":180,"minimum":-180,"type":"number"},{"type":"null"}],"default":null,"description":"Observer longitude in degrees (east positive). Omit to use place or the saved default.","title":"Longitude"},"place":{"anyOf":[{"type":"string"},{"type":"null"}],"default":null,"description":"Place name to observe from instead of coordinates, e.g. 'Moab, Utah'.","title":"Place"}},"type":"object","title":"get_space_weatherArguments"},"name":"get_space_weather","outputSchema":{"type":"object","additionalProperties":true,"title":"get_space_weatherDictOutput"}},{"annotations":{"idempotentHint":true,"openWorldHint":true,"readOnlyHint":true},"description":"Upcoming rocket launches worldwide with times, rockets, missions, pads and webcasts.\n\nUse for 'when is the next SpaceX/Starship launch' or 'any launches I could see from here'\n(max_distance_km filters to nearby pads). Schedules change often, so prefer this over memory.\n","inputSchema":{"properties":{"limit":{"default":10,"description":"Maximum launches","maximum":25,"minimum":1,"title":"Limit","type":"integer"},"search":{"anyOf":[{"type":"string"},{"type":"null"}],"default":null,"description":"Filter by rocket, provider or mission text, e.g. 'Starship', 'Rocket Lab'","title":"Search"},"max_distance_km":{"anyOf":[{"exclusiveMinimum":0,"type":"number"},{"type":"null"}],"default":null,"description":"Only launches from pads within this distance of the observer","title":"Max Distance Km"},"latitude":{"anyOf":[{"maximum":90,"minimum":-90,"type":"number"},{"type":"null"}],"default":null,"description":"Observer latitude in degrees (north positive). Omit to use place or the saved default.","title":"Latitude"},"longitude":{"anyOf":[{"maximum":180,"minimum":-180,"type":"number"},{"type":"null"}],"default":null,"description":"Observer longitude in degrees (east positive). Omit to use place or the saved default.","title":"Longitude"},"place":{"anyOf":[{"type":"string"},{"type":"null"}],"default":null,"description":"Place name to observe from instead of coordinates, e.g. 'Moab, Utah'.","title":"Place"}},"type":"object","title":"get_upcoming_launchesArguments"},"name":"get_upcoming_launches","outputSchema":{"type":"object","additionalProperties":true,"title":"get_upcoming_launchesDictOutput"}}]}}
```
