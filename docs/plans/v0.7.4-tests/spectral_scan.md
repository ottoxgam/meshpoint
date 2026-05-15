# Spectral-Scan Noise Floor — Test Checklist

Validates the SX1302 spectral scan path (`src/hal/sx1302_spectral_scan.py`, `src/api/telemetry/spectral_scan_service.py`) and its plumbing through `NoiseFloorTracker` to the sidebar telemetry rail.

The previous packet-derived noise estimate stays as a fallback for installs whose `libloragw` build does not expose the spectral-scan symbols. Both paths need verifying.

## Status

- [ ] Hardware-validated on `.141` (RAK V2)
- [ ] Hardware-validated on `.15` (SenseCap M1)
- [ ] Browser-only checks complete

## Pre-conditions

- Service running on the target unit (`sudo systemctl status meshpoint`).
- `radio.spectral_scan_interval_seconds` left at the default (60) unless explicitly testing the override.
- Dashboard logged in as admin.

## 1. First scan publishes within startup window

- [ ] Restart the service: `sudo systemctl restart meshpoint`.
- [ ] Within ~10–15 seconds the journal logs `SpectralScanService started: <freq> MHz, every 60s, first scan in 10s`.
- [ ] Within another 10 seconds the sidebar telemetry rail's noise-floor readout switches from `calibrating` to a real number (e.g. `-118 dBm`) without needing a packet to arrive first.
- [ ] Hovering the readout shows the spectral-scan tooltip variant (mentions "SX1302 spectral scan", not "packet-derived upper bound").

## 2. Reading agrees with a reference monitor

- [ ] Tune a Waveshare SX1262 HAT (or any single-channel SDR) to the same frequency as `radio.frequency_mhz` and the same bandwidth (`radio.bandwidth_khz`).
- [ ] Compare the dashboard reading to the reference monitor's RSSI scan over the same window.
- [ ] Numbers should agree within ~3 dB. If the gap is larger, the rssi_offset calibration in `_configure_rf_chains` is suspect.

## 3. Cadence and RX impact

- [ ] Tail `journalctl -u meshpoint -f` for ~3 minutes.
- [ ] One spectral-scan log line at DEBUG level (`Spectral scan: <freq> MHz floor=...`) appears every 60 seconds (give or take ~1 s).
- [ ] Packet RX continues normally throughout. No noticeable gap (>1 received packet drop attributable to the scan window).

## 4. Disable via config

- [ ] Set `radio.spectral_scan_interval_seconds: 0` in `local.yaml`.
- [ ] Restart. The journal logs `Spectral scan disabled via radio.spectral_scan_interval_seconds`.
- [ ] The sidebar readout starts in `calibrating` and stays there until packets arrive, at which point it shows the packet-derived fallback value.
- [ ] Hovering the readout shows the fallback tooltip variant ("packet-derived upper bound", "spectral scan was not available on this device").

## 5. Configurable cadence

- [ ] Set `radio.spectral_scan_interval_seconds: 300` in `local.yaml`.
- [ ] Restart. The journal logs `every 300s` in the service-start line.
- [ ] Subsequent scan log lines arrive ~5 minutes apart.
- [ ] Set `radio.spectral_scan_interval_seconds: 1` (intentionally too low). Restart. The service clamps to 5 s minimum and the journal still reports usable cadence (no scan storm).

## 6. Frequency change reflects in scans

- [ ] Edit `radio.frequency_mhz` to a different in-band value via the dashboard Configuration page.
- [ ] Restart. The journal `SpectralScanService started` line carries the new frequency.
- [ ] After the next scan, the sidebar readout's tooltip mentions the new frequency.

## 7. HAL graceful degradation

- [ ] On a unit whose `libloragw` is older than the patched HAL we ship (or temporarily symlink `/usr/local/lib/libloragw.so` to a stripped build for the test), restart the service.
- [ ] The journal logs `libloragw does not expose lgw_spectral_scan_*; spectral scan disabled, falling back to packet-derived noise floor`.
- [ ] No scan log lines appear at the configured cadence.
- [ ] The sidebar readout still populates from packet-derived data after the first 3+ packets arrive.

## 8. Frontend sparkline

- [ ] Watch the sidebar telemetry-rail noise sparkline for ~5 minutes.
- [ ] One new sample appears per scan interval (12 samples in 12 minutes at default cadence).
- [ ] Sparkline shape is smooth — discrete steps as expected, no gaps or spikes that would suggest dropped frames over the websocket.

## Acceptance

- [ ] All 8 sections green on `.141`.
- [ ] All 8 sections green on `.15`.
- [ ] Reference-monitor side-by-side (section 2) within ~3 dB on at least one of the units.
- [ ] No regression in CRC_BAD or CRC_OK packet rates compared to the same window before the spectral scan service was wired in.
