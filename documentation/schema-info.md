
## MOD LOOKUP  (You can mostly ignore this):
| Bit Flag | Code | Name        | Description |
|----------|------|-------------|-------------|
| 1        | NF   | No Fail     | You can’t fail—your HP won’t drop below 1. |
| 2        | EZ   | Easy        | Halves overall difficulty: circles are larger, approach rate & HP drain are reduced. |
| 4        | TD   | Touch Device | Optimized input for touchscreens (no penalty for misses, auto-hits spinners). |
| 8        | HD   | Hidden      | Hit objects fade out shortly after appearing—tests your reading & timing reflexes. |
| 16       | HR   | Hard Rock   | Increases overall difficulty: smaller circles, faster SR, higher HP drain, flipped playfield. |
| 32       | SD   | Sudden Death | One miss (or 50/100 hit) ends the run immediately. |
| 64       | DT   | Double Time | +50% speed and +1.12× AR & CS—makes the map play faster. |
| 128      | RX   | Relax       | You don’t need to click—game auto-hits for you, but you still move the cursor. |
| 256      | HT   | Half Time   | −25% speed and −1.12× AR & CS—slows the map way down. |
| 512      | NC   | Nightcore   | All the effects of DT plus a higher-pitched soundtrack and special effects. (always appears together with DT) |
| 1024     | FL   | Flashlight  | Only a small spotlight around the cursor is visible—everything else is dark. |
| 2048     | AU   | Auto        | The game plays itself perfectly for you (100% accuracy, full combo). |
| 4096     | SO   | Spun Out    | Spinners automatically finish themselves—no need to spin at all. |
| 8192     | AP   | Auto Pilot  | Cursor movement is automated—only your clicks matter (still need to click in time). |
| 16384    | PF   | Perfect     | Like SD but even stricter: you must hit every note with 300s—no 100s or 50s allowed. |
| 32768    | K4   | Key4        | Forces a 4-key playfield (for mania mode). |
| 65536    | K5   | Key5        | Forces a 5-key playfield (mania mode). *(mania mode is excluded from our data)* |
| 131072   | K6   | Key6        | Forces a 6-key playfield (mania mode). |
| 262144   | K7   | Key7        | Forces a 7-key playfield (mania mode). |
| 524288   | K8   | Key8        | Forces an 8-key playfield (mania mode). |
| 1048576  | FI   | Fade In     | Hit objects are completely invisible until their approach circle reaches them. |
| 2097152  | RN   | Random      | Randomly shuffles the horizontal positions of hit objects (mania only). *(mania mode is excluded from our data)* |


## PREPOCESSING STEP THAT IS IMPORTANT TO REMEMBER:
to make the huge amount of modding and beatmap combinations managable and avoid **item-explosion**. The following steps were taken.
1. Parsed the Bitmasks into human readable format (a string set)
2. Filtered out all rows where difficulty/map/pp altering Mods were used, except for the competetively viable (and most common) ones.
3. Merged all "preference" mods if used, that change gameplay only a little into the remaining 4 main categories:  
**NM**(No Mod),**DT**(Double Time), **HR**(Hard Rock), **DTHR**(Double Time + Hardrock)  
    - **HD**(Hidden) was also collapsed, it changes diff and pp slightly, and is widely used. The max,pp score was kept in the collapsing. 

4. treat each beatmap_id + Mod_string combination as a unique item and assign a new "item id": *mod_beatmap_id*


---

## 📁 `beatmaps.csv`



Each row represents a unique combination of a **beatmap** and a **mod configuration**

| Column | Description |
|--------|-------------|
| `mod_beatmap_id` | Unique hash ID for a specific beatmap and modification combination. | 
| `beatmap_id` | Original beatmap ID in osu!. |
| `mods_string` | Active modification(s) (See mod-info.txt) |
| `beatmapset_id` | Group ID for related beatmaps (e.g., same song with different difficulties). |
| `creator_user_id` | ID of the user who created the beatmap. |
| `playcount` | How many times this beatmap was played globally. |
| `passcount` | How many times players finished this beatmap. |
| `set_favourite_count` | Number of users who favorited the beatmap set. |
| `artist` | Artist of the song. |
| `title` | Title of the song used |
| `submit_date`, `approved_date` | When was the beatmap set published, and when was it approved for ranked |
| `bpm` | Beats per minute of the song (tempo). |
| `hit_length` | Duration of playable part (in seconds). |
| `count_total`, `count_normal`, `count_slider`, `count_spinner` | Number of total objects and their breakdown. |
| `diff_drain` | How quickly a player’s health drains during mistakes. Higher values make survival harder. |
| `diff_size` | The size of the hit circles. Higher values make circles smaller and harder to hit. |
| `diff_overall` | Strictness of the timing window to hit notes correctly. Higher values require more precision. |
| `diff_approach` | Speed at which notes appear and fade. Higher values give less time to react. |
| `diff_star_rating` | Star rating representing unified difficulty calculated from mapping data |
| `aim`, `speed` | dynmically calculated from mapping data, represent something similar to distance of hit objects and hits/per second required |
| `max_combo` | Maximum combo possible. |
| `strain` | Overall difficulty strain of the beatmap, usually a weighted combination of aim and speed strains. rolling windows of aim and speed difficulty. (since these may vary over the map)
| `slider_factor` | Ratio of sliders to total hit objects.
| `speed_note_count` | Number of notes that appear in quick succession and are considered to contribute to speed difficulty. Typically counts note pairs where the time between them is below a threshold (e.g., 200 ms). |
| `genre` | Genre of the song. |
| `language` | Language of the lyrics or theme. |

---

## 📁 `scores.csv`

Each row represents the best score a user playing a specific beatmap with a specific modification achieved. 

| Column | Description |
|--------|-------------|
| `score_id` | Unique row ID for this score (generated). |
| `mod_beatmap_id` | Matches the `mod_beatmap_id` in `beatmaps.csv`. |
| `beatmap_id` | The beatmap that was played. |
| `mods_string` | Modification(s) used during play. |
| `user_id` | ID of the player. |
| `score` | Total score earned (game-specific metric). |
| `pp` | Performance points — a normalized skill score, used for player rankings|
| `accuracy` | weighted ratio of hit accuracy and misses |
| `maxcombo` | Maximum combo achieved in this play. (consequtive hits withouth missing an object) |
| `rank` | Letter rank awarded (e.g., `A`, `S`, `X`). according to certain accuracy/combo requirements, but does not really matter |
| `date` | Date the play occurred. |
| `playcount` | Total playcount of the user on this beatmap (ATTENTION NOT MOD SPECIFIC)|

---

## 📁 `users.csv`

Each row represents an **osu! player profile**.

| Column | Description |
|--------|-------------|
| `user_id` | Unique user ID. |
| `username` | Player's username. |
| `accuracy` | global accuracy (according to an faq this considers only hits to miss over all plays). |
| `accuracy_new` | global Updated accuracy metric (this uses a weighted calculation depending on how accurate the hits are, maybe not over all plays? tends to be higher than the old one) |
| `playcount` | Total number of completed beatmaps plays. |
| `rank` | Global rank of the player . |
| `fail_count` | Number of failed attempts. |
| `exit_count` | Number of early exits or retries. (among other things potentially relevant to identify "farm players")|
| `max_combo` | Highest combo achieved on any play. |
| `country_acronym` | Country code (e.g., `US`, `JP`). |
| `last_played` | Timestamp of the most recent play. |
| `total_seconds_played` | Total time spent playing (in seconds). |


### Nice to have, if possible obtain these when i have the time and a way without the osu api banning me:
- max pp of a beatmap_mod id
- liked beatmap- sets of users
- exist/failrate on beatmap
