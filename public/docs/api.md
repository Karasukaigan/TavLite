## GET /api/version

Retrieve the application version.

**Example Response:**
```json
{ "version": "TavLite v1.1.0" }
```

---

## POST /api/script

Load Funscript script data.

**Request Body (JSON):** Full Funscript file content, which must include the `actions` field.

**Response:** Result of script loading.

---

## GET /api/script/play?at=0

Start playing the script from the specified time (in milliseconds).

---

## GET /api/script/stop

Stop the currently playing script.

---

## POST /api/script/custom

Generate and play a script using a custom motion pattern.

**Request Body (JSON) Fields:**
- `range`: Motion range limit, default is 100  
- `inverted`: Whether to invert the motion, default is False  
- `max_pos`: Maximum position, default is 100  
- `min_pos`: Minimum position, default is 0  
- `freq`: Frequency, default is 1.0  
- `decline_ratio`: Decline phase ratio, default is 0.5 (i.e., triangular waveform)  
- `start_pos`: Starting position, default is None  
- `loop_count`: Number of loops, default is 100  
- `custom_actions`: Custom `actions` array; if provided, it overrides all other settings except `loop_count`, default is None  

---

## GET /api/offset?ms=100

Adjust the global time offset in milliseconds.

**Parameters:**
- `ms`: Offset adjustment value (not the total offset), integer, can be positive or negative

**Example Response:**
```json
{
  "message": "Offset adjusted successfully",
  "old_offset": 0,
  "new_offset": 100,
  "adjustment": 100
}
```