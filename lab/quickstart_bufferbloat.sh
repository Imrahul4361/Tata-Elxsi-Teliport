#!/usr/bin/env bash
# VeriQ Day-0 lab: real bufferbloat measurements in an emulated home network.
#
# EMULATION NOTICE: the ISP bottleneck (line rate + oversized FIFO buffer) is emulated
# with tc tbf (+ netem for base RTT) inside Linux network namespaces. Results show the
# method and the queue physics, not the behaviour of any specific ISP.
#
#   lan (client) --- rtr (home gateway: arm under test) --- isp (bloated bottleneck) --- srv (internet)
#
# Usage:   sudo lab/quickstart_bufferbloat.sh [arm ...]      default arms: fifo shortfifo fq_codel cake
# Arms:    fifo      stock router: queue builds in the ISP's oversized FIFO
#          shortfifo shaper just below line rate with a short tail-drop buffer (no AQM, no fairness)
#          fq_codel  smart AQM but no shaper: router is not the bottleneck, so (almost) nothing changes
#          cake      shaper just below line rate + CAKE AQM, per-host fairness, diffserv4
# Tunables (env): DOWN_MBIT UP_MBIT BASE_RTT_MS ISP_BUF_MS SHAPE_PCT DURATION OUT
set -euo pipefail

DOWN_MBIT=${DOWN_MBIT:-20}
UP_MBIT=${UP_MBIT:-5}
BASE_RTT_MS=${BASE_RTT_MS:-20}
ISP_BUF_MS=${ISP_BUF_MS:-300}
SHAPE_PCT=${SHAPE_PCT:-95}
DURATION=${DURATION:-20}
OUT=${OUT:-results/$(date +%Y%m%d-%H%M%S)}
ARMS=("$@")
[ ${#ARMS[@]} -eq 0 ] && ARMS=(fifo shortfifo fq_codel cake)

HERE=$(cd "$(dirname "$0")" && pwd)
NS_LAN=vq-lan NS_RTR=vq-rtr NS_ISP=vq-isp NS_SRV=vq-srv
SRV4=10.10.3.2 SRV6=fd00:10:3::2
V6=0
NETEM_OK=0
[ -d /proc/sys/net/ipv6 ] && V6=1  # dual-stack where the kernel has IPv6 enabled

die() { echo "error: $*" >&2; exit 1; }
warn() { echo "warning: $*" >&2; }
nsx() { local ns=$1; shift; ip netns exec "$ns" "$@"; }
bytes_per_sec() { echo $(( $1 * 1000000 / 8 )); }
burst_bytes() { local b=$(( $1 / 100 )); echo $(( b > 16000 ? b : 16000 )); }  # ~10 ms of data, >= 16 kB

preflight() {
  [ "$(id -u)" -eq 0 ] || die "run with sudo"
  for c in ip tc iperf3 ping python3; do
    command -v "$c" >/dev/null || die "missing $c (sudo apt install iproute2 iperf3 iputils-ping python3)"
  done
  for m in sch_tbf sch_netem sch_fq_codel sch_cake; do
    modprobe "$m" 2>/dev/null || warn "could not load $m (if an arm fails: sudo apt install linux-modules-extra-$(uname -r))"
  done
}

cleanup() {
  for ns in $NS_LAN $NS_RTR $NS_ISP $NS_SRV; do
    if ip netns list | grep -qw "$ns"; then
      ip netns pids "$ns" | xargs -r kill 2>/dev/null || true
      ip netns del "$ns"
    fi
  done
}

link() {  # link <nsA> <ifA> <nsB> <ifB>
  ip link add "$2" type veth peer name "$4"
  ip link set "$2" netns "$1"
  ip link set "$4" netns "$3"
}

addr() {  # addr <ns> <if> <ipv4/cidr> <ipv6/cidr>
  nsx "$1" ip addr add "$3" dev "$2"
  [ $V6 -eq 0 ] || nsx "$1" ip -6 addr add "$4" dev "$2" nodad
  nsx "$1" ip link set "$2" up
}

isp_bottleneck() {
  local dn up
  dn=$(bytes_per_sec "$DOWN_MBIT")
  up=$(bytes_per_sec "$UP_MBIT")
  # the "modem": line rate with a deliberately oversized FIFO (ISP_BUF_MS deep), as in many real CPEs
  nsx $NS_ISP tc qdisc replace dev isp-cpe root tbf rate "${DOWN_MBIT}mbit" \
    burst "$(burst_bytes "$dn")" limit $(( dn * ISP_BUF_MS / 1000 ))
  nsx $NS_ISP tc qdisc replace dev isp-net root tbf rate "${UP_MBIT}mbit" \
    burst "$(burst_bytes "$up")" limit $(( up * ISP_BUF_MS / 1000 ))
  # base internet RTT, added on the server side
  if nsx $NS_SRV tc qdisc replace dev srv0 root netem delay "${BASE_RTT_MS}ms" limit 10000; then
    NETEM_OK=1
  else
    warn "netem unavailable: running without the ${BASE_RTT_MS} ms base RTT"
  fi
}

setup() {
  cleanup
  for ns in $NS_LAN $NS_RTR $NS_ISP $NS_SRV; do
    ip netns add "$ns"
    nsx "$ns" ip link set lo up
  done
  link $NS_LAN lan0 $NS_RTR rtr-lan
  link $NS_RTR rtr-wan $NS_ISP isp-cpe
  link $NS_ISP isp-net $NS_SRV srv0
  addr $NS_LAN lan0    10.10.1.2/24 fd00:10:1::2/64
  addr $NS_RTR rtr-lan 10.10.1.1/24 fd00:10:1::1/64
  addr $NS_RTR rtr-wan 10.10.2.1/24 fd00:10:2::1/64
  addr $NS_ISP isp-cpe 10.10.2.2/24 fd00:10:2::2/64
  addr $NS_ISP isp-net 10.10.3.1/24 fd00:10:3::1/64
  addr $NS_SRV srv0    10.10.3.2/24 fd00:10:3::2/64
  nsx $NS_LAN ip route add default via 10.10.1.1
  nsx $NS_RTR ip route add default via 10.10.2.2
  nsx $NS_ISP ip route add 10.10.1.0/24 via 10.10.2.1
  nsx $NS_SRV ip route add default via 10.10.3.1
  for ns in $NS_RTR $NS_ISP; do
    nsx "$ns" sysctl -qw net.ipv4.ip_forward=1
  done
  if [ $V6 -eq 1 ]; then
    nsx $NS_LAN ip -6 route add default via fd00:10:1::1
    nsx $NS_RTR ip -6 route add default via fd00:10:2::2
    nsx $NS_ISP ip -6 route add fd00:10:1::/64 via fd00:10:2::1
    nsx $NS_SRV ip -6 route add default via fd00:10:3::1
    for ns in $NS_RTR $NS_ISP; do
      nsx "$ns" sysctl -qw net.ipv6.conf.all.forwarding=1
    done
  fi
  # segmentation offloads off, so every shaper sees real wire-sized packets
  if command -v ethtool >/dev/null; then
    local ns dev
    for pair in "$NS_LAN lan0" "$NS_RTR rtr-lan" "$NS_RTR rtr-wan" "$NS_ISP isp-cpe" "$NS_ISP isp-net" "$NS_SRV srv0"; do
      read -r ns dev <<<"$pair"
      nsx "$ns" ethtool -K "$dev" gso off gro off tso off >/dev/null 2>&1 || true
    done
  fi
  isp_bottleneck
  nsx $NS_SRV iperf3 -s -D >/dev/null
  sleep 1
}

apply_arm() {  # returns non-zero if the kernel lacks what the arm needs
  local arm=$1 ds us
  ds=$(( DOWN_MBIT * 1000 * SHAPE_PCT / 100 ))
  us=$(( UP_MBIT * 1000 * SHAPE_PCT / 100 ))
  for dev in rtr-lan rtr-wan; do
    nsx $NS_RTR tc qdisc del dev "$dev" root 2>/dev/null || true
  done
  case $arm in
    fifo) ;;
    shortfifo)  # rtr-lan egress shapes the download, rtr-wan egress shapes the upload
      nsx $NS_RTR tc qdisc replace dev rtr-lan root tbf rate "${ds}kbit" \
        burst "$(burst_bytes $(( ds * 125 )))" latency 15ms &&
      nsx $NS_RTR tc qdisc replace dev rtr-wan root tbf rate "${us}kbit" \
        burst "$(burst_bytes $(( us * 125 )))" latency 15ms ;;
    fq_codel)
      nsx $NS_RTR tc qdisc replace dev rtr-lan root fq_codel &&
      nsx $NS_RTR tc qdisc replace dev rtr-wan root fq_codel ;;
    cake)
      nsx $NS_RTR tc qdisc replace dev rtr-lan root cake bandwidth "${ds}kbit" diffserv4 dual-dsthost &&
      nsx $NS_RTR tc qdisc replace dev rtr-wan root cake bandwidth "${us}kbit" diffserv4 dual-srchost ;;
    *) die "unknown arm: $arm" ;;
  esac
}

measure() {  # measure <arm> <down|up>
  local arm=$1 dir=$2 tag="$OUT/${1}_${2}" rflag=() load_pid
  [ "$dir" = down ] && rflag=(-R)
  nsx $NS_LAN ping -n -i 0.2 -c 15 "$SRV4" >"$tag.idle.ping" || true
  nsx $NS_LAN iperf3 -c "$SRV4" "${rflag[@]}" -P 4 -t "$DURATION" -J >"$tag.iperf.json" &
  load_pid=$!
  sleep 3  # let TCP fill the queue
  nsx $NS_LAN ping -n -i 0.1 -c $(( (DURATION - 5) * 10 )) "$SRV4" >"$tag.load.ping" || true
  wait "$load_pid" || warn "iperf3 failed for $arm/$dir"
  python3 -I "$HERE/summarize.py" "$arm" "$dir" "$tag" >>"$OUT/summary.csv"
}

main() {
  preflight
  trap cleanup EXIT
  mkdir -p "$OUT"
  setup
  if [ $V6 -eq 0 ]; then
    warn "IPv6 is disabled in this kernel: running IPv4 only"
  elif nsx $NS_LAN ping -6 -n -c 3 "$SRV6" >"$OUT/ipv6_check.ping"; then
    echo "IPv6 path: OK"
  else
    warn "IPv6 path failed (see $OUT/ipv6_check.ping)"
  fi
  python3 -I "$HERE/summarize.py" --header >"$OUT/summary.csv"
  for arm in "${ARMS[@]}"; do
    if ! apply_arm "$arm" 2>"$OUT/${arm}_apply.err"; then
      warn "skipping arm '$arm': kernel lacks a required qdisc ($(head -1 "$OUT/${arm}_apply.err"))"
      continue
    fi
    for dir in down up; do
      echo ">> arm=$arm direction=$dir (${DURATION}s)"
      measure "$arm" "$dir"
    done
  done
  {
    echo "EMULATION: ISP bottleneck = tbf ${DOWN_MBIT}/${UP_MBIT} Mbit with a ${ISP_BUF_MS} ms FIFO"
    if [ $NETEM_OK -eq 1 ]; then echo "base RTT: ${BASE_RTT_MS} ms (netem applied)"; else echo "base RTT: NOT applied (netem unavailable)"; fi
    if [ $V6 -eq 1 ]; then echo "IPv6: enabled"; else echo "IPv6: unavailable in this kernel (IPv4 only)"; fi
    echo "arms requested: ${ARMS[*]}"
    echo "kernel: $(uname -r)"
    echo "tc: $(tc -V)"
    echo "iperf3: $(iperf3 --version | head -1)"
    echo "shaper: ${SHAPE_PCT}% of line rate; load: 4 TCP flows x ${DURATION}s"
  } >"$OUT/environment.txt"
  echo
  python3 -I "$HERE/summarize.py" --table "$OUT/summary.csv"
  echo
  echo "added_p95_ms = p95 RTT under load minus idle median RTT (the bufferbloat your call feels)"
  echo "raw data + environment fingerprint: $OUT/"
}

main
