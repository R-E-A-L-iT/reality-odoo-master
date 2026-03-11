/** @odoo-module **/

document.addEventListener("DOMContentLoaded", async () => {
    const host = document.getElementById("three-product-canvas");
    if (!host || !window.THREE || !THREE.OBJLoader) {
        return;
    }

    const scene = new THREE.Scene();
    scene.background = new THREE.Color(0xf5f5f5);

    const camera = new THREE.PerspectiveCamera(
        45,
        host.clientWidth / host.clientHeight,
        0.1,
        1000
    );
    camera.position.set(0, 1, 5);

    const renderer = new THREE.WebGLRenderer({ antialias: true, alpha: true });
    renderer.setSize(host.clientWidth, host.clientHeight);
    renderer.setPixelRatio(Math.min(window.devicePixelRatio, 2));
    host.appendChild(renderer.domElement);

    const ambient = new THREE.AmbientLight(0xffffff, 1.5);
    scene.add(ambient);

    const directional = new THREE.DirectionalLight(0xffffff, 2);
    directional.position.set(3, 5, 4);
    scene.add(directional);

    const loader = new THREE.OBJLoader();
    loader.load("/prowebsite/static/src/models/BLK2GO_Adapter.obj", (obj) => {
        const box = new THREE.Box3().setFromObject(obj);
        const center = box.getCenter(new THREE.Vector3());
        const size = box.getSize(new THREE.Vector3());

        obj.position.sub(center);

        const maxAxis = Math.max(size.x, size.y, size.z);
        const scale = 2 / maxAxis;
        obj.scale.setScalar(scale);

        scene.add(obj);
    });

    function animate() {
        requestAnimationFrame(animate);
        scene.rotation.y += 0.002;
        renderer.render(scene, camera);
    }
    animate();

    window.addEventListener("resize", () => {
        const w = host.clientWidth;
        const h = host.clientHeight;
        camera.aspect = w / h;
        camera.updateProjectionMatrix();
        renderer.setSize(w, h);
    });
});