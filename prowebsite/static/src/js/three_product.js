/** @odoo-module **/

import { whenReady } from "@odoo/owl";

console.log("three_product.js file loaded");

whenReady(async () => {
    console.log("three_product.js whenReady fired");

    const host = document.getElementById("three-product-canvas");
    console.log("host =", host);

    if (!host) {
        console.warn("No #three-product-canvas found");
        return;
    }

    let THREE;
    let OBJLoader;

    try {
        // Keep both imports on the exact same Three.js version
        THREE = await import("https://cdnjs.cloudflare.com/ajax/libs/three.js/0.180.0/three.module.js");
        ({ OBJLoader } = await import("https://cdn.jsdelivr.net/npm/three@0.180.0/examples/jsm/loaders/OBJLoader.js"));
        console.log("Three.js loaded from CDN", THREE);
        console.log("OBJLoader loaded from CDN", OBJLoader);
    } catch (err) {
        console.error("Failed to load Three.js from CDN:", err);
        return;
    }

    const scene = new THREE.Scene();
    scene.background = new THREE.Color(0xf4f4f4);

    const camera = new THREE.PerspectiveCamera(
        45,
        host.clientWidth / host.clientHeight,
        0.1,
        1000
    );
    camera.position.set(0, 0, 5);

    const renderer = new THREE.WebGLRenderer({
        antialias: true,
        alpha: false,
    });
    renderer.setPixelRatio(Math.min(window.devicePixelRatio, 2));
    renderer.setSize(host.clientWidth, host.clientHeight);
    host.appendChild(renderer.domElement);

    const ambientLight = new THREE.AmbientLight(0xffffff, 2.2);
    scene.add(ambientLight);

    const hemiLight = new THREE.HemisphereLight(0xffffff, 0x888888, 1.8);
    hemiLight.position.set(0, 1, 0);
    scene.add(hemiLight);

    const dirLight1 = new THREE.DirectionalLight(0xffffff, 2.5);
    dirLight1.position.set(5, 8, 6);
    scene.add(dirLight1);

    const dirLight2 = new THREE.DirectionalLight(0xffffff, 1.5);
    dirLight2.position.set(-5, 3, -4);
    scene.add(dirLight2);

    let model = null;

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

            const box = new THREE.Box3().setFromObject(obj);
            const center = box.getCenter(new THREE.Vector3());
            const size = box.getSize(new THREE.Vector3());

            obj.position.x -= center.x;
            obj.position.y -= center.y;
            obj.position.z -= center.z;

            const maxAxis = Math.max(size.x, size.y, size.z);
            if (maxAxis > 0) {
                const scale = 2.2 / maxAxis;
                obj.scale.setScalar(scale);
            }

            model = obj;
            scene.add(model);

            camera.position.set(0, 0.3, 4);
            camera.lookAt(0, 0, 0);

            console.log("OBJ loaded successfully", obj);
        },
        undefined,
        function (error) {
            console.error("Error loading OBJ:", error);
        }
    );

    function animate() {
        requestAnimationFrame(animate);

        if (model) {
            model.rotation.y += 0.01;
        }

        renderer.render(scene, camera);
    }
    animate();

    window.addEventListener("resize", () => {
        const width = host.clientWidth;
        const height = host.clientHeight;

        camera.aspect = width / height;
        camera.updateProjectionMatrix();
        renderer.setSize(width, height);
    });
});