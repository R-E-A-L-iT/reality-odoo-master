/** @odoo-module **/

import { whenReady } from "@odoo/owl";

console.log("three_product.js file loaded");

whenReady(async () => {
    console.log("three_product.js whenReady fired");

    const host = document.getElementById("three-product-canvas");
    if (!host) {
        console.warn("No #three-product-canvas found");
        return;
    }

    let THREE;
    let OBJLoader;

    try {
        THREE = await import("https://esm.sh/three@0.180.0");
        ({ OBJLoader } = await import("https://esm.sh/three@0.180.0/examples/jsm/loaders/OBJLoader.js"));
        console.log("Three.js loaded from CDN", THREE);
        console.log("OBJLoader loaded from CDN", OBJLoader);
    } catch (err) {
        console.error("Failed to load Three.js from CDN:", err);
        return;
    }

    const scene = new THREE.Scene();

    const camera = new THREE.PerspectiveCamera(
        45,
        host.clientWidth / host.clientHeight,
        0.1,
        1000
    );
    camera.position.set(0, 0, 5);

    const renderer = new THREE.WebGLRenderer({
        antialias: true,
        alpha: true,
    });
    renderer.setPixelRatio(Math.min(window.devicePixelRatio, 2));
    renderer.setSize(host.clientWidth, host.clientHeight);
    renderer.setClearColor(0x000000, 0);
    renderer.domElement.style.position = "absolute";
    renderer.domElement.style.inset = "0";
    renderer.domElement.style.zIndex = "2";
    renderer.domElement.style.background = "transparent";
    host.appendChild(renderer.domElement);

    const ambientLight = new THREE.AmbientLight(0xffffff, 2.0);
    scene.add(ambientLight);

    const hemiLight = new THREE.HemisphereLight(0xffffff, 0x444444, 1.6);
    hemiLight.position.set(0, 1, 0);
    scene.add(hemiLight);

    const dirLight1 = new THREE.DirectionalLight(0xffffff, 2.2);
    dirLight1.position.set(5, 8, 6);
    scene.add(dirLight1);

    const dirLight2 = new THREE.DirectionalLight(0xffffff, 1.2);
    dirLight2.position.set(-5, 3, -4);
    scene.add(dirLight2);

    let model = null;
    let modelWrapper = null;

    let dropAnimationStart = null;
    const dropDuration = 1400;

    // Mouse interaction state
    let mouseTargetX = 0;
    let mouseTargetY = 0;
    let mouseCurrentX = 0;
    let mouseCurrentY = 0;

    // How far the model can be pushed from center
    const maxOffsetX = 0.35;
    const maxOffsetY = 0.22;

    // How quickly it eases toward the target
    const mouseEase = 0.06;

    const loader = new OBJLoader();
    loader.load(
        "/prowebsite/static/src/models/BLK2GO_Adapter.obj",
        function (obj) {
            obj.traverse(function (child) {
                if (child.isMesh) {
                    child.material = new THREE.MeshNormalMaterial({
                        side: THREE.DoubleSide,
                    });
                }
            });

            const initialBox = new THREE.Box3().setFromObject(obj);
            const initialSize = initialBox.getSize(new THREE.Vector3());
            const maxAxis = Math.max(initialSize.x, initialSize.y, initialSize.z);

            if (maxAxis > 0) {
                const scale = 1.1 / maxAxis;
                obj.scale.setScalar(scale);
            }

            const box = new THREE.Box3().setFromObject(obj);
            const center = box.getCenter(new THREE.Vector3());
            const size = box.getSize(new THREE.Vector3());

            obj.position.set(-center.x, -center.y, -center.z);

            // Fixed tilt
            obj.rotation.x = -0.25;
            obj.rotation.z = 0.12;

            model = obj;

            modelWrapper = new THREE.Group();
            modelWrapper.add(model);
            scene.add(modelWrapper);

            const fitHeightDistance = size.y / (2 * Math.tan((Math.PI * camera.fov) / 360));
            const fitWidthDistance = fitHeightDistance / camera.aspect;
            const distance = 1.8 * Math.max(fitHeightDistance, fitWidthDistance, size.z, 2);

            camera.position.set(0, 0, distance || 4);
            camera.lookAt(0, 0, 0);

            // Start above the viewport and settle into center
            modelWrapper.position.set(0, 3.5, 0);
            dropAnimationStart = performance.now();

            console.log("OBJ loaded successfully", obj);
        },
        undefined,
        function (error) {
            console.error("Error loading OBJ:", error);
        }
    );

    function easeOutCubic(t) {
        return 1 - Math.pow(1 - t, 3);
    }

    function clamp(value, min, max) {
        return Math.max(min, Math.min(max, value));
    }

    function updateMouseTarget(clientX, clientY) {
        const rect = host.getBoundingClientRect();
        const centerX = rect.left + rect.width / 2;
        const centerY = rect.top + rect.height / 2;

        // Normalize to roughly -1 to 1
        const nx = (clientX - centerX) / (rect.width / 2);
        const ny = (clientY - centerY) / (rect.height / 2);

        // Push opposite the mouse direction, but only slightly
        mouseTargetX = clamp(-nx, -1, 1) * maxOffsetX;
        mouseTargetY = clamp(ny, -1, 1) * maxOffsetY;
    }

    host.addEventListener("mousemove", (event) => {
        updateMouseTarget(event.clientX, event.clientY);
    });

    host.addEventListener("mouseleave", () => {
        mouseTargetX = 0;
        mouseTargetY = 0;
    });

    host.addEventListener("touchmove", (event) => {
        if (event.touches && event.touches[0]) {
            updateMouseTarget(event.touches[0].clientX, event.touches[0].clientY);
        }
    }, { passive: true });

    host.addEventListener("touchend", () => {
        mouseTargetX = 0;
        mouseTargetY = 0;
    });

    function animate(now) {
        requestAnimationFrame(animate);

        // Smooth mouse interaction
        mouseCurrentX += (mouseTargetX - mouseCurrentX) * mouseEase;
        mouseCurrentY += (mouseTargetY - mouseCurrentY) * mouseEase;

        let baseY = 0;

        if (modelWrapper && dropAnimationStart !== null) {
            const elapsed = now - dropAnimationStart;
            const progress = Math.min(elapsed / dropDuration, 1);
            const eased = easeOutCubic(progress);

            baseY = 3.5 * (1 - eased);

            if (progress >= 1) {
                dropAnimationStart = null;
                baseY = 0;
            }
        }

        if (modelWrapper) {
            modelWrapper.position.x = mouseCurrentX;
            modelWrapper.position.y = baseY + mouseCurrentY;
            modelWrapper.rotation.y += 0.01;
        }

        renderer.render(scene, camera);
    }
    animate(performance.now());

    window.addEventListener("resize", () => {
        const width = host.clientWidth;
        const height = host.clientHeight;

        camera.aspect = width / height;
        camera.updateProjectionMatrix();
        renderer.setSize(width, height);
        camera.lookAt(0, 0, 0);
    });
});