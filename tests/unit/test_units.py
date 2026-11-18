import pytest

from specbridge.extraction import units as U


@pytest.mark.parametrize(
    "text,expected",
    [
        ("-40 °C … +85 °C", (-40, 85)),
        ("–40 to 85 °C", (-40, 85)),  # en dash sign
        ("-40...+85 °C", (-40, 85)),
        ("-40 °C to +85 °C", (-40, 85)),
        ("-40…+85 °C", (-40, 85)),
        ("0 to 70 °C", (0, 70)),
        ("0…55 °C", (0, 55)),
        ("-25 - +70 °C", (-25, 70)),
        ("-20 °C … -5 °C", (-20, -5)),
        ("24 V DC (18–30 V)", (18, 30)),
        ("18…30 V DC", (18, 30)),
        ("18 to 30 V DC", (18, 30)),
        ("18...30 V", (18, 30)),
        ("18-30 V DC", (18, 30)),
        ("19,2…28,8 V DC", (19.2, 28.8)),
        ("200 to 480 V AC", (200, 480)),
        ("88~132VAC", (88, 132)),
        ("10 – 30 V DC", (10, 30)),
        ("100 - 240", (100, 240)),
    ],
)
def test_parse_range(text, expected):
    assert U.parse_range(text) == expected


@pytest.mark.parametrize(
    "s,v",
    [
        ("1,5", 1.5),
        ("0,5", 0.5),
        ("1.5", 1.5),
        ("12", 12),
        ("1.234,5", 1234.5),
        ("1,234.5", 1234.5),
        ("3,000", 3000),
        ("0,500", 0.5),
        ("2,5", 2.5),
        ("22,5", 22.5),
    ],
)
def test_parse_number(s, v):
    assert U.parse_number(s) == pytest.approx(v)
    assert U.parse_number("abc") is None


def test_numbers_in_signs():
    assert U.numbers_in("-25 °C … +70 °C") == [-25, 70]
    assert U.numbers_in("45 × 110 × 70 mm") == [45, 110, 70]
    assert U.numbers_in("4–20 mA") == [4, 20]  # dash between digits is a separator
    assert U.numbers_in("IP67") == [67]


@pytest.mark.parametrize(
    "value,unit,target,expected",
    [
        (500, "mA", "A", 0.5),
        (1.5, "kW", "W", 1500),
        (1.8, "kg", "g", 1800),
        (0.5, "A", "A", 0.5),
        (230, "V AC", "V", 230),
        (230, "VAC", "V", 230),
        (24, "V DC", "V", 24),
        (45, "mm", "mm", 45),
        (4.5, "cm", "mm", 45),
        (1, "in", "mm", 25.4),
        (85, "°C", "degC", 85),
        (185, "°F", "degC", 85),
        (358.15, "K", "degC", 85),
        (5, None, "V", 5),
        (1, "kV", "V", 1000),
        (1000, "mV", "V", 1),
    ],
)
def test_convert(value, unit, target, expected):
    assert U.convert(value, unit, target) == pytest.approx(expected, rel=1e-4)


def test_convert_incompatible_returns_none():
    assert U.convert(5, "kg", "V") is None
    assert U.convert(5, "bogusunit", "V") is None


@pytest.mark.parametrize(
    "text,ip",
    [
        ("IP 67", "IP67"),
        ("IP67", "IP67"),
        ("ip65", "IP65"),
        ("IP 69K", "IP69K"),
        ("IP67/IP69K", "IP69K"),
        ("IP 65; IP 67; IP 69K", "IP69K"),
        ("Degree of protection IP20", "IP20"),
    ],
)
def test_normalize_ip(text, ip):
    assert U.normalize_ip(text) == ip


def test_normalize_ip_invalid():
    assert U.normalize_ip("protection class III") is None
    assert U.normalize_ip("IP7X") is None


def test_alias_maps():
    assert U.canonical_interfaces("IO Link, Modbus-RTU; PROFINET IO") == [
        "IO-Link",
        "Modbus RTU",
        "PROFINET",
    ]
    assert U.canonical_interfaces(["4–20 mA", "4...20 mA", "EtherCAT"]) == ["4-20 mA", "EtherCAT"]
    assert U.canonical_interfaces("Ethernet/IP") == ["Ethernet/IP"]
    assert U.canonical_certs("CE, UL Listed, c-UL-us, RoHS compliant, UKCA") == [
        "CE",
        "UL",
        "cULus",
        "RoHS",
        "UKCA",
    ]
    assert U.canonical_certs(["UL 508 approved", "TÜV"]) == ["UL", "TÜV"]
    assert U.canonical_category("Inductive Proximity Sensor") == "sensor"
    assert U.canonical_category("Servo Drive") == "drive"
    assert U.canonical_category("I/O module") == "io_module"
    assert U.canonical_category("Power supply") == "power_supply"
    assert U.canonical_category("Widget") == "other"
