/** @odoo-module **/

// ─────────────────────────────────────────────────────────────────────────────
// RTC Series — scroll-scrubbed 3D model section
//
// Self-contained Three.js scene that mirrors the OmniGO "Capture" scroll
// animation (three_product.js): as the user scrolls the model rotates, scales
// and reveals four feature callouts. The positioning / rotation maths are kept
// identical to OmniGO on purpose — the only differences here are:
//   • it uses the animated RTC GLB (New_RTC_series_Animated.glb)
//   • the GLB's embedded animation is played on a continuous loop
//   • the callout copy is RTC-specific (with fr_CA / es_ES translations)
//
// The host element id (#three-rtc-canvas-scroll) is deliberately different from
// the OmniGO ids so three_product.js early-exits on this page and never touches
// this scene.
// ─────────────────────────────────────────────────────────────────────────────

import { whenReady } from "@odoo/owl";

whenReady(async () => {
    const scrollHost = document.getElementById("three-rtc-canvas-scroll");
    if (!scrollHost) return; // not on the RTC page

    // ── i18n ─────────────────────────────────────────────────────────────────
    const pageLang = (document.documentElement.lang || "en_US").replace("-", "_");

    const _i18n = {
        fr_CA: {
            calloutStub:    "Embase de trépied",
            calloutPower:   "Batteries et caméras VIS",
            calloutHandle:  "Poignée et antennes",
            detailStubTitle:   "Embase RTC et fixation au trépied",
            detailStubBody:    "Se monte en quelques secondes sur l'embase 5/8″ d'un trépied léger Leica GST80, avec des adaptateurs optionnels pour trépieds topographiques standard et embases de tribrach — le scanner s'intègre directement à votre configuration d'arpentage existante.",
            detailPulseTitle:  "Technologie à double impulsion",
            detailPulseBody:   "La télémétrie à double impulsion en vol émet une seconde impulsion laser avant le retour de la première, maintenant des cadences de numérisation élevées même à longue portée. Associée au temps de vol à numérisation de forme d'onde (WFD) à grande dynamique, elle offre des mesures rapides et à faible bruit.",
            detailPowerTitle:  "Batteries et caméras VIS",
            detailPowerBody:   "Deux batteries Li-Ion Leica GEB461 remplaçables à chaud offrent jusqu'à quatre heures de numérisation continue, tandis que les caméras du système inertiel visuel (VIS) situées à proximité suivent la position du scanner en temps réel pour un pré-recalage automatique et sans cible.",
            detailHandleTitle: "Poignée et antennes",
            detailHandleBody:  "Une poignée ergonomique sur le dessus facilite le transport et le repositionnement du scanner entre les installations, tandis que les antennes WLAN (2,4 / 5 GHz) et GNSS intégrées assurent la connexion pour les flux de travail infonuagiques Livelink et les données géoréférencées.",
            mobileStub:    "Embase de trépied",
            mobilePulse:   "Technologie à double impulsion",
            mobilePower:   "Batteries et caméras VIS",
            mobileHandle:  "Poignée et antennes",
        },
        es_ES: {
            calloutStub:    "Montaje en stub",
            calloutPower:   "Baterías y cámaras VIS",
            calloutHandle:  "Asa y antenas",
            detailStubTitle:   "Stub RTC y fijación al trípode",
            detailStubBody:    "Se monta en segundos sobre el stub de 5/8″ de un trípode ligero Leica GST80, con adaptadores opcionales para trípodes topográficos estándar y bases de tribrach — el escáner se integra directamente en su configuración de topografía existente.",
            detailPulseTitle:  "Tecnología de doble pulso",
            detailPulseBody:   "La medición de doble pulso en aire emite un segundo pulso láser antes de que regrese el primero, manteniendo altas velocidades de escaneo incluso a largo alcance. Combinada con el tiempo de vuelo de digitalización de forma de onda (WFD) de alta dinámica, ofrece mediciones rápidas y de bajo ruido.",
            detailPowerTitle:  "Baterías y cámaras VIS",
            detailPowerBody:   "Dos baterías de ión-litio Leica GEB461 intercambiables en caliente ofrecen hasta cuatro horas de escaneo continuo, mientras que las cámaras del sistema inercial visual (VIS) situadas junto a ellas rastrean la posición del escáner en tiempo real para un prerregistro automático y sin dianas.",
            detailHandleTitle: "Asa y antenas",
            detailHandleBody:  "Un asa ergonómica en la parte superior facilita transportar y reposicionar el escáner entre configuraciones, mientras que las antenas WLAN (2,4 / 5 GHz) y GNSS integradas lo mantienen conectado para los flujos de trabajo en la nube Livelink y los datos georreferenciados.",
            mobileStub:    "Montaje en stub",
            mobilePulse:   "Tecnología de doble pulso",
            mobilePower:   "Baterías y cámaras VIS",
            mobileHandle:  "Asa y antenas",
        },
    };

    function _t(key, fallback) {
        const dict = _i18n[pageLang];
        if (!dict) return fallback;
        const val = dict[key];
        return val === undefined ? fallback : val;
    }

    // ── Three.js + GLTFLoader + EXRLoader (loaded from CDN, same as OmniGO) ─────
    let THREE, GLTFLoader, EXRLoader, LoopRepeat;
    try {
        const [threeModule, gltfModule, exrModule] = await Promise.all([
            import("https://esm.sh/three@0.180.0"),
            import("https://esm.sh/three@0.180.0/examples/jsm/loaders/GLTFLoader.js"),
            import("https://esm.sh/three@0.180.0/examples/jsm/loaders/EXRLoader.js"),
        ]);
        THREE = threeModule;
        ({ GLTFLoader } = gltfModule);
        ({ EXRLoader } = exrModule);
        LoopRepeat = THREE.LoopRepeat;
    } catch (err) {
        console.error("[rtc-scroll] Failed to load Three.js:", err);
        return;
    }

    const modelPath = "/prowebsite/static/src/models/New_RTC_series_Animated.glb";
    const hdriPath  = "/prowebsite/static/src/hdri/studio_kontrast_04_2k.exr";

    // ── Maths helpers (identical to three_product.js) ──────────────────────────
    const clamp = (v, min, max) => Math.max(min, Math.min(max, v));
    const easeOutCubic = (t) => 1 - Math.pow(1 - t, 3);
    const easeInOutCubic = (t) => (t < 0.5 ? 4 * t * t * t : 1 - Math.pow(-2 * t + 2, 3) / 2);
    const lerp = (a, b, t) => a + (b - a) * t;

    function createRenderer(targetHost, zIndex = "1") {
        const renderer = new THREE.WebGLRenderer({ antialias: true, alpha: true });
        renderer.setPixelRatio(Math.min(window.devicePixelRatio, 2));
        renderer.setSize(targetHost.clientWidth, targetHost.clientHeight);
        renderer.setClearColor(0x000000, 0);
        // Correct colour pipeline + filmic tone mapping so the HDRI-lit, light-
        // coloured RTC housing reads naturally instead of blown-out.
        renderer.outputColorSpace = THREE.SRGBColorSpace;
        renderer.toneMapping = THREE.ACESFilmicToneMapping;
        renderer.toneMappingExposure = 0.9;
        renderer.domElement.style.position = "absolute";
        renderer.domElement.style.inset = "0";
        renderer.domElement.style.zIndex = zIndex;
        renderer.domElement.style.background = "transparent";
        targetHost.appendChild(renderer.domElement);
        return renderer;
    }

    // Load the studio EXR and use it as an image-based-lighting environment map.
    // We deliberately do NOT set scene.background — the canvas stays transparent
    // so the red section gradient shows through behind the model. The HDRI only
    // drives lighting and reflections via scene.environment.
    function applyEnvironment(renderer, scene) {
        const pmrem = new THREE.PMREMGenerator(renderer);
        pmrem.compileEquirectangularShader();

        new EXRLoader().load(
            hdriPath,
            (texture) => {
                const envMap = pmrem.fromEquirectangular(texture).texture;
                scene.environment = envMap;
                texture.dispose();
                pmrem.dispose();
            },
            undefined,
            (err) => {
                console.error("[rtc-scroll] EXR HDRI failed to load:", err);
                pmrem.dispose();
            }
        );
    }

    // Minimal lighting — the HDRI environment does the heavy lifting now, so we
    // only add a soft ambient/key plus a barely-there red rim for brand warmth.
    function addSoftProductLights(scene) {
        scene.add(new THREE.AmbientLight(0xffffff, 0.2));

        const key = new THREE.DirectionalLight(0xffffff, 0.8);
        key.position.set(5, 5, 5);
        scene.add(key);

        const redRim = new THREE.DirectionalLight(0xff2222, 0.08);
        redRim.position.set(-5, 2, 4);
        scene.add(redRim);
    }

    // Normalise an object the same way OmniGO does: double-sided materials,
    // scale so its largest axis is 1.1 units, and recentre on the origin.
    function normaliseObject(obj) {
        obj.traverse((child) => {
            if (child.isMesh && child.material) {
                if (Array.isArray(child.material)) {
                    child.material = child.material.map((mat) => {
                        if (!mat) return mat;
                        const cloned = mat.clone();
                        cloned.side = THREE.DoubleSide;
                        cloned.needsUpdate = true;
                        return cloned;
                    });
                } else {
                    child.material = child.material.clone();
                    child.material.side = THREE.DoubleSide;
                    child.material.needsUpdate = true;
                }
            }
        });

        obj.updateMatrixWorld(true);

        const initialBox = new THREE.Box3().setFromObject(obj);
        const initialSize = initialBox.getSize(new THREE.Vector3());
        const maxAxis = Math.max(initialSize.x, initialSize.y, initialSize.z);
        if (maxAxis > 0) obj.scale.setScalar(1.1 / maxAxis);

        obj.updateMatrixWorld(true);

        const meshBox = new THREE.Box3();
        obj.traverse((child) => { if (child.isMesh) meshBox.expandByObject(child); });
        const center = meshBox.isEmpty()
            ? new THREE.Box3().setFromObject(obj).getCenter(new THREE.Vector3())
            : meshBox.getCenter(new THREE.Vector3());
        obj.position.set(-center.x, -center.y, -center.z);

        return obj;
    }

    // ── Scene / camera / renderer ──────────────────────────────────────────────
    const scrollScene = new THREE.Scene();
    const scrollCamera = new THREE.PerspectiveCamera(
        45,
        scrollHost.clientWidth / scrollHost.clientHeight,
        0.1,
        1000
    );
    scrollCamera.position.set(0, 0, 5);

    const scrollRenderer = createRenderer(scrollHost, "1");
    applyEnvironment(scrollRenderer, scrollScene);
    addSoftProductLights(scrollScene);

    const scrollSection = scrollHost.closest(".o_three_scroll_section");

    let scrollModel = null;     // pitch (rotation.x) is applied here
    let scrollWrapper = null;   // yaw / roll / scale / position applied here
    let mixer = null;           // drives the looping GLB animation
    const clock = new THREE.Clock();

    // ── Feature callouts / detail panel / mobile labels (DOM) ──────────────────
    // Four scroll phases reveal four faces of the RTC scanner:
    //   _attachment → tripod stub mount   (Stub)
    //   _back       → dual-pulse ranging  (Pulse)
    //   _hatch      → batteries & VIS cams (Power)
    //   _screw      → handle & antennas   (Handle)
    let _elDetailStub = null, _elDetailPulse = null, _elDetailPower = null, _elDetailHandle = null;
    let _elMobileStub = null, _elMobilePulse = null, _elMobilePower = null, _elMobileHandle = null;

    const _mqLarge = window.matchMedia("(min-width: 992px)");
    let _isLargeScreen = _mqLarge.matches;
    _mqLarge.addEventListener("change", (e) => { _isLargeScreen = e.matches; });
    const isLargeScreen = () => _isLargeScreen;

    function createScrollHotspots() {
        const hotspotLayer = document.createElement("div");
        hotspotLayer.className = "o_three_scroll_hotspot_layer";
        hotspotLayer.innerHTML = `
            <div class="o_three_feature_callout o_three_feature_callout_attachment">
                <div class="o_three_feature_dot"></div>
                <div class="o_three_feature_line_diagonal"></div>
                <div class="o_three_feature_line_under"></div>
                <div class="o_three_feature_label">${_t("calloutStub", "Tripod Stub Mount")}</div>
            </div>
            <div class="o_three_feature_callout o_three_feature_callout_hatch">
                <div class="o_three_feature_dot"></div>
                <div class="o_three_feature_line_diagonal"></div>
                <div class="o_three_feature_line_under"></div>
                <div class="o_three_feature_label">${_t("calloutPower", "Batteries &amp; VIS Cameras")}</div>
            </div>
            <div class="o_three_feature_callout o_three_feature_callout_screw">
                <div class="o_three_feature_dot"></div>
                <div class="o_three_feature_line_diagonal"></div>
                <div class="o_three_feature_line_under"></div>
                <div class="o_three_feature_label">${_t("calloutHandle", "Handle &amp; Antennas")}</div>
            </div>
        `;
        scrollHost.appendChild(hotspotLayer);

        const detailPanel = document.createElement("div");
        detailPanel.className = "o_three_scroll_detail_panel";
        detailPanel.innerHTML = `
            <div class="o_three_scroll_feature_detail o_three_scroll_feature_detail_attachment">
                <h3 class="o_three_scroll_feature_title">${_t("detailStubTitle", "RTC Stub &amp; Tripod Attachment")}</h3>
                <p class="o_three_scroll_feature_body">${_t("detailStubBody", "Mounts in seconds on the 5/8″ stub of a lightweight Leica GST80 tripod, with optional adapters for standard topographic tripods and survey tribrach bases — so the scanner drops straight into your existing survey setup.")}</p>
            </div>
            <div class="o_three_scroll_feature_detail o_three_scroll_feature_detail_back">
                <h3 class="o_three_scroll_feature_title">${_t("detailPulseTitle", "Dual-Pulse Technology")}</h3>
                <p class="o_three_scroll_feature_body">${_t("detailPulseBody", "Dual-pulse-in-air ranging launches a second laser pulse before the first returns, sustaining high scan rates even at long range. Combined with high-dynamic Waveform Digitising (WFD) time-of-flight, it delivers fast, low-noise measurements.")}</p>
            </div>
            <div class="o_three_scroll_feature_detail o_three_scroll_feature_detail_hatch">
                <h3 class="o_three_scroll_feature_title">${_t("detailPowerTitle", "Batteries &amp; VIS Cameras")}</h3>
                <p class="o_three_scroll_feature_body">${_t("detailPowerBody", "Two hot-swappable Leica GEB461 Li-Ion batteries provide up to four hours of continuous scanning, while the Visual Inertial System (VIS) cameras alongside them track the scanner's position in real time for automatic, targetless pre-registration.")}</p>
            </div>
            <div class="o_three_scroll_feature_detail o_three_scroll_feature_detail_screw">
                <h3 class="o_three_scroll_feature_title">${_t("detailHandleTitle", "Handle &amp; Antennas")}</h3>
                <p class="o_three_scroll_feature_body">${_t("detailHandleBody", "An ergonomic top handle keeps the scanner easy to carry and reposition between setups, while the integrated WLAN (2.4 / 5 GHz) and GNSS antennas keep it connected for Livelink cloud workflows and georeferenced data.")}</p>
            </div>
        `;
        scrollHost.appendChild(detailPanel);

        const mobileLabels = document.createElement("div");
        mobileLabels.className = "o_three_scroll_mobile_labels";
        mobileLabels.innerHTML = `
            <div class="o_three_scroll_mobile_label o_three_scroll_mobile_label_attachment">${_t("mobileStub", "Tripod Stub Mount")}</div>
            <div class="o_three_scroll_mobile_label o_three_scroll_mobile_label_back">${_t("mobilePulse", "Dual-Pulse Technology")}</div>
            <div class="o_three_scroll_mobile_label o_three_scroll_mobile_label_hatch">${_t("mobilePower", "Batteries &amp; VIS Cameras")}</div>
            <div class="o_three_scroll_mobile_label o_three_scroll_mobile_label_screw">${_t("mobileHandle", "Handle &amp; Antennas")}</div>
        `;
        scrollHost.appendChild(mobileLabels);

        _elDetailStub   = detailPanel.querySelector(".o_three_scroll_feature_detail_attachment");
        _elDetailPulse  = detailPanel.querySelector(".o_three_scroll_feature_detail_back");
        _elDetailPower  = detailPanel.querySelector(".o_three_scroll_feature_detail_hatch");
        _elDetailHandle = detailPanel.querySelector(".o_three_scroll_feature_detail_screw");
        _elMobileStub   = mobileLabels.querySelector(".o_three_scroll_mobile_label_attachment");
        _elMobilePulse  = mobileLabels.querySelector(".o_three_scroll_mobile_label_back");
        _elMobilePower  = mobileLabels.querySelector(".o_three_scroll_mobile_label_hatch");
        _elMobileHandle = mobileLabels.querySelector(".o_three_scroll_mobile_label_screw");
    }

    // ── Scroll timing constants (identical to three_product.js) ────────────────
    const TRANS_VH        = 0.55;
    const DWELL_VH        = 0.50;
    const RETURN_VH       = 0.55;
    const TOTAL_SCROLL_VH = 4 * (TRANS_VH + DWELL_VH) + RETURN_VH;

    const SCROLL_TRANS  = TRANS_VH  / TOTAL_SCROLL_VH;
    const SCROLL_DWELL  = DWELL_VH  / TOTAL_SCROLL_VH;
    const SCROLL_PHASE  = SCROLL_TRANS + SCROLL_DWELL;
    const SCROLL_RETURN = RETURN_VH  / TOTAL_SCROLL_VH;

    function setScrollSectionHeight() {
        if (!scrollSection) return;
        const scrollablePx = TOTAL_SCROLL_VH * window.innerHeight;
        scrollSection.style.minHeight = `${Math.round(scrollablePx + window.innerHeight)}px`;
    }

    let scrollAnimProgress = 0;

    function updateScrollHotspots() {
        const show = (el, on) => el && el.classList.toggle("is-visible", on);
        const p = scrollAnimProgress;
        const T = SCROLL_TRANS, PH = SCROLL_PHASE;
        const inA = p >= T          && p <= PH;
        const inB = p >= PH + T     && p <= PH * 2;
        const inH = p >= PH * 2 + T && p <= PH * 3;
        const inS = p >= PH * 3 + T && p <= PH * 4;
        show(_elDetailStub,  inA); show(_elDetailPulse,  inB);
        show(_elDetailPower, inH); show(_elDetailHandle, inS);
        show(_elMobileStub,  inA); show(_elMobilePulse,  inB);
        show(_elMobilePower, inH); show(_elMobileHandle, inS);
    }

    function updateScrollSectionProgress() {
        if (!scrollSection) return;

        const rect = scrollSection.getBoundingClientRect();
        const viewportH = window.innerHeight || document.documentElement.clientHeight;
        const sectionActive = rect.top <= viewportH && rect.bottom >= 0;

        scrollHost.classList.toggle("is-active", sectionActive);
        if (!sectionActive) return;

        const scrollableDistance = rect.height - viewportH;
        if (scrollableDistance <= 0) {
            scrollAnimProgress = 0;
            return;
        }
        scrollAnimProgress = clamp(-rect.top / scrollableDistance, 0, 1);
    }

    // Pose maths copied verbatim from three_product.js applyScrollSectionPose().
    function applyScrollSectionPose() {
        if (!scrollModel || !scrollWrapper) return;

        const t = scrollAnimProgress;

        const baseY = -Math.PI / 12;
        const baseZ = Math.PI / 12;

        const TOP_PITCH    = -Math.PI * 0.455;
        const SIDE_PITCH   = -Math.PI * 0.056;
        const BOTTOM_PITCH =  Math.PI * 0.433;

        const T  = SCROLL_TRANS;
        const PH = SCROLL_PHASE;

        const p1 = easeInOutCubic(clamp(t / T, 0, 1));
        const p2 = easeInOutCubic(clamp((t - PH)     / T, 0, 1));
        const p3 = easeInOutCubic(clamp((t - PH * 2) / T, 0, 1));
        const p4 = easeInOutCubic(clamp((t - PH * 3) / T, 0, 1));
        const p5 = easeOutCubic(clamp((t - PH * 4) / SCROLL_RETURN, 0, 1));

        const desktop    = isLargeScreen();
        const scaleStart = desktop ? 1.50 : 1.30;
        const scalePeak  = desktop ? 1.85 : 1.55;

        let scale;
        if (t < PH) {
            scale = lerp(scaleStart, scalePeak, p1);
        } else if (t < PH * 4) {
            scale = scalePeak;
        } else {
            scale = lerp(scalePeak, scaleStart, p5);
        }
        scrollWrapper.scale.setScalar(scale);

        let targetX;
        if (!desktop) {
            targetX = 0;
        } else if (t < PH) {
            targetX = lerp(0, -0.7, p1);
        } else if (t < PH * 4) {
            targetX = -0.7;
        } else {
            targetX = lerp(-0.7, 0, p5);
        }
        scrollWrapper.position.set(targetX, 0, 0);

        let modelX;
        if (t < PH) {
            modelX = lerp(0, TOP_PITCH, p1);
        } else if (t < PH * 2) {
            modelX = lerp(TOP_PITCH, 0, p2);
        } else if (t < PH * 3) {
            modelX = lerp(0, SIDE_PITCH, p3);
        } else if (t < PH * 4) {
            modelX = lerp(SIDE_PITCH, BOTTOM_PITCH, p4);
        } else {
            modelX = lerp(BOTTOM_PITCH, 0, p5);
        }
        scrollModel.rotation.x = modelX;
        scrollModel.rotation.y = 0;
        scrollModel.rotation.z = 0;

        let wrapperY;
        if (t < PH) {
            wrapperY = baseY;
        } else if (t < PH * 2) {
            wrapperY = lerp(baseY, baseY + Math.PI, p2);
        } else if (t < PH * 3) {
            wrapperY = lerp(baseY + Math.PI, baseY + Math.PI * 0.5, p3);
        } else if (t < PH * 4) {
            wrapperY = lerp(baseY + Math.PI * 0.5, baseY, p4);
        } else {
            wrapperY = baseY;
        }
        scrollWrapper.rotation.y = wrapperY;

        let wrapperZ;
        if (t < PH) {
            wrapperZ = lerp(baseZ, baseZ * 0.4, p1);
        } else if (t < PH * 4) {
            wrapperZ = baseZ * 0.4;
        } else {
            wrapperZ = lerp(baseZ * 0.4, baseZ, p5);
        }
        scrollWrapper.rotation.z = wrapperZ;
        scrollWrapper.rotation.x = 0;

        updateScrollHotspots();
    }

    // ── Load the animated RTC model ────────────────────────────────────────────
    const gltfLoader = new GLTFLoader();
    gltfLoader.load(
        modelPath,
        (gltf) => {
            const inner = gltf.scene;

            // Disable shadows.
            inner.traverse((child) => {
                if (!child.isMesh) return;
                child.castShadow = false;
                child.receiveShadow = false;
            });

            normaliseObject(inner);

            // Nesting: scrollWrapper → scrollModel → inner.
            // The pose code writes scrollModel.rotation (pitch) and scrollWrapper
            // (yaw/roll/scale/position). `inner` is left untouched so its embedded
            // animation can play without being overwritten every frame.
            scrollModel = new THREE.Group();
            scrollModel.add(inner);

            scrollWrapper = new THREE.Group();
            scrollWrapper.add(scrollModel);
            scrollWrapper.position.set(0, 0, 0);
            scrollScene.add(scrollWrapper);

            // Play the embedded animation on a continuous loop.
            if (gltf.animations && gltf.animations.length > 0) {
                mixer = new THREE.AnimationMixer(inner);
                gltf.animations.forEach((clip) => {
                    const action = mixer.clipAction(clip);
                    action.setLoop(LoopRepeat, Infinity);
                    action.clampWhenFinished = false;
                    action.enabled = true;
                    action.play();
                });
            } else {
                console.warn("[rtc-scroll] RTC model has no animations — showing static.");
            }

            setScrollSectionHeight();
            applyScrollSectionPose();
        },
        undefined,
        (error) => {
            console.error("[rtc-scroll] RTC model failed to load:", error);
        }
    );

    createScrollHotspots();
    setScrollSectionHeight();

    // ── Resize (debounced) ─────────────────────────────────────────────────────
    let _resizeTimer = null;
    window.addEventListener("resize", () => {
        clearTimeout(_resizeTimer);
        _resizeTimer = setTimeout(() => {
            setScrollSectionHeight();
            scrollCamera.aspect = scrollHost.clientWidth / scrollHost.clientHeight;
            scrollCamera.updateProjectionMatrix();
            scrollRenderer.setSize(scrollHost.clientWidth, scrollHost.clientHeight);
        }, 150);
    }, { passive: true });

    // ── Scroll dirty flag — only recompute pose when the page scrolls ──────────
    const _scrollRoot = document.getElementById("wrapwrap") || document.documentElement;
    let _scrollDirty = true;
    _scrollRoot.addEventListener("scroll", () => { _scrollDirty = true; }, { passive: true });

    // Skip GPU work when the section is off-screen.
    let _scrollSectionInView = false;
    if (scrollSection) {
        new IntersectionObserver(([e]) => { _scrollSectionInView = e.isIntersecting; }, { threshold: 0 })
            .observe(scrollSection);
    }

    // ── Animation loop ─────────────────────────────────────────────────────────
    let _lastScrollProgress = -1;
    function animate() {
        requestAnimationFrame(animate);

        if (_scrollDirty) {
            _scrollDirty = false;
            updateScrollSectionProgress();
        }

        if (scrollAnimProgress !== _lastScrollProgress) {
            _lastScrollProgress = scrollAnimProgress;
            applyScrollSectionPose();
        }

        // Always advance the looping model animation.
        const delta = clock.getDelta();
        if (mixer) mixer.update(delta);

        if (_scrollSectionInView) {
            scrollRenderer.render(scrollScene, scrollCamera);
        }
    }
    requestAnimationFrame(animate);
});
