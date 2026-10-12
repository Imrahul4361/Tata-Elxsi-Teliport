# Allowed references (cite as [R#]; do not add others)

**Queue management and congestion**
- R1. J. Gettys, K. Nichols, "Bufferbloat: Dark Buffers in the Internet", ACM Queue 9(11), 2011.
- R2. K. Nichols, V. Jacobson, "Controlling Queue Delay", ACM Queue 10(5), 2012.
- R3. RFC 8289, "Controlled Delay Active Queue Management" (CoDel), 2018.
- R4. RFC 8290, "The Flow Queue CoDel Packet Scheduler and Active Queue Management Algorithm", 2018.
- R5. T. Høiland-Jørgensen, D. Täht, J. Morton, "Piece of CAKE: A Comprehensive Queue Management Solution for Home Gateways", IEEE LANMAN 2018 (arXiv:1804.07617).
- R6. tc-cake(8) manual page (iproute2): https://manpages.debian.org/unstable/iproute2/tc-cake.8.en.html
- R7. tc-hfsc(8), tc-htb(8), tc-fq_codel(8), tc-ctinfo(8), tc-mirred(8) manual pages (iproute2).
- R8. I. Stoica, H. Zhang, T. S. E. Ng, "A Hierarchical Fair Service Curve Algorithm for Link-Sharing, Real-Time and Priority Services", ACM SIGCOMM 1997.
- R9. N. Cardwell et al., "BBR: Congestion-Based Congestion Control", ACM Queue 14(5), 2016.
- R10. Bufferbloat project, "What can I do about Bufferbloat?": https://www.bufferbloat.net/projects/bloat/wiki/What_can_I_do_about_Bufferbloat/

**Tools and comparators**
- R11. sqm-scripts: https://github.com/tohojo/sqm-scripts and OpenWrt SQM guide: https://openwrt.org/docs/guide-user/network/traffic-shaping/sqm-details
- R12. cake-autorate: https://github.com/lynxthecat/cake-autorate
- R13. QoSmate (v0.5.48 @ c507843): https://github.com/hudra0/qosmate and luci-app-qosmate (v1.0.14): https://github.com/hudra0/luci-app-qosmate
- R14. qosify (OpenWrt package for DSCP-based classification with CAKE), OpenWrt source tree.
- R15. Waveform bufferbloat test: https://www.waveform.com/tools/bufferbloat

**Standards and drafts**
- R16. RFC 792, Internet Control Message Protocol (incl. Timestamp/Timestamp Reply), 1981.
- R17. RFC 2474, Definition of the Differentiated Services Field (DS Field), 1998; RFC 4594, Configuration Guidelines for DiffServ Service Classes, 2006.
- R18. RFC 8325, Mapping Diffserv to IEEE 802.11, 2018.
- R19. RFC 3168, The Addition of Explicit Congestion Notification (ECN) to IP, 2001.
- R20. RFC 9330, 9331, 9332: Low Latency, Low Loss, and Scalable Throughput (L4S) architecture, ECN protocol, DualQ Coupled AQM, 2023.
- R21. RFC 9956, A Non-Queue-Building Per-Hop Behavior (NQB PHB), May 2026: https://www.rfc-editor.org/rfc/rfc9956.html
- R22. RFC 9946, UDP Speed Test Protocol for IP capacity (UDPST), Apr 2026: https://www.rfc-editor.org/rfc/rfc9946.html; Broadband Forum TR-471.
- R23. draft-ietf-ippm-responsiveness-09 (RPM): https://www.ietf.org/archive/id/draft-ietf-ippm-responsiveness-09.html
- R24. draft-ietf-ippm-qoo-11, Quality of Outcome: https://datatracker.ietf.org/doc/draft-ietf-ippm-qoo
- R25. draft-livingood-low-latency-deployment-16: https://www.ietf.org/ietf-ftp/internet-drafts/draft-livingood-low-latency-deployment-16.html
- R26. ITU-T G.107, The E-model: https://www.itu.int/ITU-T/recommendations/rec.aspx?rec=12505
- R27. Broadband Forum TR-181 (Device:2 data model) and TR-369 (User Services Platform, USP): https://usp.bbf.org/

**Measurement, ML and statistics**
- R28. M. Jain, C. Dovrolis, "Pathload: a measurement tool for end-to-end available bandwidth", PAM 2002 (SLoPS).
- R29. A. N. Angelopoulos, S. Bates, "A Gentle Introduction to Conformal Prediction and Distribution-Free Uncertainty Quantification", arXiv:2107.07511.
- R30. V. Vovk, A. Gammerman, G. Shafer, Algorithmic Learning in a Random World, Springer, 2005.
- R31. G. Ke et al., "LightGBM: A Highly Efficient Gradient Boosting Decision Tree", NeurIPS 2017.
- R32. Zhao et al., "The Sweet Danger of Sugar", ACM SIGCOMM 2025: https://arxiv.org/abs/2507.16438
- R33. Sharma et al., "Estimating WebRTC Video QoE Metrics Without Using Application Headers", ACM IMC 2023: https://arxiv.org/abs/2306.01194
- R34. CESNET DataZoo datasets: https://cesnet.github.io/cesnet-datazoo/datasets_overview/
- R35. W3C, Identifiers for WebRTC's Statistics API: https://www.w3.org/TR/webrtc-stats/ ; MDN RTCInboundRtpStreamStats: https://developer.mozilla.org/en-US/docs/Web/API/RTCInboundRtpStreamStats
- R36. R. Jain, D. Chiu, W. Hawe, "A Quantitative Measure of Fairness and Discrimination for Resource Allocation in Shared Computer Systems", DEC-TR-301, 1984.
- R37. B. Efron, R. Tibshirani, An Introduction to the Bootstrap, Chapman & Hall, 1993.
- R38. S. Holm, "A Simple Sequentially Rejective Multiple Test Procedure", Scandinavian Journal of Statistics 6(2), 1979.
- R39. J. Brooke, "SUS: A 'quick and dirty' usability scale", 1996.

**Platforms and tooling**
- R40. OpenWrt documentation: procd init scripts https://openwrt.org/docs/guide-developer/procd-init-scripts ; UCI https://openwrt.org/docs/guide-user/base-system/uci ; SDK https://openwrt.org/docs/guide-developer/toolchain/using_the_sdk ; dnsmasq IP sets https://openwrt.org/docs/guide-user/base-system/dhcp#ip_sets
- R41. LuCI (OpenWrt web interface), client-side JavaScript API: https://github.com/openwrt/luci
- R42. nftables wiki: https://wiki.nftables.org
- R43. The Go programming language: https://go.dev ; three.js: https://threejs.org ; uPlot: https://github.com/leeoniya/uPlot ; Mermaid: https://mermaid.js.org ; dash.js: https://github.com/Dash-Industry-Forum/dash.js ; Jitsi handbook: https://jitsi.github.io/handbook/
- R44. prpl Foundation (prplOS): https://prplfoundation.org/ ; RDK (RDK-B): https://rdkcentral.com/
- R45. Government of India, The Digital Personal Data Protection Act, 2023 (MeitY).

**Tata Elxsi and TELIPORT** (from docs/01; use only as docs/01 uses them)
- R46. Tata Elxsi NEURON autonomous network platform: https://www.tataelxsi.com/platforms/neuron-autonomous-network-platform
- R47. Tata Elxsi Q1 FY27 press release: https://www.tataelxsi.com/news-and-events/press-releases/tata-elxsi-delivers-steady-growth-at-28-qoq-and-145-yoy-in-q1-fy27
- R48. Tata Elxsi investor presentations (NSE filings): https://nsearchives.nseindia.com/corporate/TELNSE_14072026183436_SEIntimationPresentation.pdf
- R49. Tata Elxsi RDK-B launch coverage: https://www.angelone.in/news/share-market/tata-elxsi-launches-rdkb
- R50. TELIPORT Season 4 listings: https://gradpartners.in/e/Tata-Elxsi-TELIPORT-Season-4-347 ; https://unstop.com/hackathons/tata-elxsi-teliport-season-4-gl-bajaj-institute-of-management-greater-noida-1767967/amp

**Project evidence**
- R51. VeriQ Day-0 sandbox evidence: repository `evidence/day0_sandbox_2026-10-11/` (preliminary, one run).
