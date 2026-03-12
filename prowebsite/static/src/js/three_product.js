/** @odoo-module **/

import { whenReady } from "@odoo/owl";

whenReady(async () => {
    const heroHost = document.getElementById("three-product-canvas");
    const bottomModelHost = document.getElementById("three-product-canvas-bottom-model");

    if (!heroHost || !bottomModelHost) {
        return;
    }

    // ----------------------------
    // Text animation
    // ----------------------------
    const textEl = heroHost.querySelector(".o_three_canvas_text");
    if (textEl) {
        const text = (textEl.textContent || "").trim();
        textEl.textContent = "";

        [...text].forEach((char, index) => {
            const span = document.createElement("span");
            span.className = "letter";
            span.textContent = char === " " ? "\u00A0" : char;
            span.style.animationDelay = `${index * 0.16}s`;
            textEl.appendChild(span);
        });

        textEl.classList.add("is-ready");
    }

    let THREE;
    let OBJLoader;
    let MTLLoader;
    let GLTFLoader;
    let OrbitControls;

    try {
        THREE = await import("https://esm.sh/three@0.180.0");
        ({ OBJLoader } = await import("https://esm.sh/three@0.180.0/examples/jsm/loaders/OBJLoader.js"));
        ({ MTLLoader } = await import("https://esm.sh/three@0.180.0/examples/jsm/loaders/MTLLoader.js"));
        ({ GLTFLoader } = await import("https://esm.sh/three@0.180.0/examples/jsm/loaders/GLTFLoader.js"));
        ({ OrbitControls } = await import("https://esm.sh/three@0.180.0/examples/jsm/controls/OrbitControls.js"));
    } catch (err) {
        console.error("Failed to load Three.js:", err);
        return;
    }

    const modelBasePath = "/prowebsite/static/src/models/";
    const animatedModelFolder = "/prowebsite/static/src/models/blk2go_with_adapter_anim/";
    const animatedTextureFolder = "/prowebsite/static/src/models/blk2go_with_adapter_anim/BLK2GO_with_Adapter_Textures/";
    const animatedModelPath = `${animatedModelFolder}scene.gltf`;

    function clamp(value, min, max) {
        return Math.max(min, Math.min(max, value));
    }

    function easeOutCubic(t) {
        return 1 - Math.pow(1 - t, 3);
    }

    function createRenderer(targetHost, zIndex = "2") {
        const renderer = new THREE.WebGLRenderer({
            antialias: true,
            alpha: true,
        });

        renderer.setPixelRatio(Math.min(window.devicePixelRatio, 2));
        renderer.setSize(targetHost.clientWidth, targetHost.clientHeight);
        renderer.setClearColor(0x000000, 0);

        // Important for glTF / PBR textures
        renderer.outputColorSpace = THREE.SRGBColorSpace;
        renderer.toneMapping = THREE.ACESFilmicToneMapping;
        renderer.toneMappingExposure = 1.0;

        renderer.domElement.style.position = "absolute";
        renderer.domElement.style.inset = "0";
        renderer.domElement.style.zIndex = zIndex;
        renderer.domElement.style.background = "transparent";

        targetHost.appendChild(renderer.domElement);
        return renderer;
    }

    function addStandardLights(scene, variant = "dark") {
        if (variant === "dark") {
            const ambient = new THREE.AmbientLight(0xffffff, 1.5);
            scene.add(ambient);

            const hemi = new THREE.HemisphereLight(0xffffff, 0x444444, 1.1);
            hemi.position.set(0, 1, 0);
            scene.add(hemi);

            const dir1 = new THREE.DirectionalLight(0xffffff, 1.8);
            dir1.position.set(5, 8, 6);
            scene.add(dir1);

            const dir2 = new THREE.DirectionalLight(0xffffff, 1.0);
            dir2.position.set(-5, 4, 5);
            scene.add(dir2);

            const front = new THREE.DirectionalLight(0xffffff, 1.4);
            front.position.set(0, 0, 8);
            front.target.position.set(0, 0, 0);
            scene.add(front);
            scene.add(front.target);
        } else {
            // Softer lighting so the model doesn't get blown out white
            const ambient = new THREE.AmbientLight(0xffffff, 1.2);
            scene.add(ambient);

            const hemi = new THREE.HemisphereLight(0xffffff, 0xbcbcbc, 1.0);
            hemi.position.set(0, 1, 0);
            scene.add(hemi);

            const dir1 = new THREE.DirectionalLight(0xffffff, 1.4);
            dir1.position.set(4, 6, 5);
            scene.add(dir1);

            const dir2 = new THREE.DirectionalLight(0xffffff, 0.75);
            dir2.position.set(-4, 3, 4);
            scene.add(dir2);

            const rim = new THREE.DirectionalLight(0xffffff, 0.9);
            rim.position.set(-2, 2, -5);
            scene.add(rim);
        }
    }

    function loadObjWithMtl({ objFile, mtlFile, onLoaded }) {
        const mtlLoader = new MTLLoader();
        mtlLoader.setPath(modelBasePath);

        mtlLoader.load(
            mtlFile,
            (materials) => {
                materials.preload();

                const objLoader = new OBJLoader();
                objLoader.setMaterials(materials);
                objLoader.setPath(modelBasePath);

                objLoader.load(
                    objFile,
                    (obj) => {
                        obj.traverse((child) => {
                            if (child.isMesh) {
                                child.castShadow = false;
                                child.receiveShadow = false;

                                if (child.material) {
                                    if (Array.isArray(child.material)) {
                                        child.material.forEach((mat) => {
                                            mat.side = THREE.DoubleSide;
                                        });
                                    } else {
                                        child.material.side = THREE.DoubleSide;
                                    }
                                }
                            }
                        });

                        onLoaded(obj);
                    },
                    undefined,
                    (error) => console.error(`Error loading OBJ ${objFile}:`, error)
                );
            },
            undefined,
            (error) => console.error(`Error loading MTL ${mtlFile}:`, error)
        );
    }

    function forceBottomModelMaterials(obj) {
        obj.traverse((child) => {
            if (!child.isMesh || !child.material) {
                return;
            }

            const materials = Array.isArray(child.material) ? child.material : [child.material];

            materials.forEach((mat) => {
                mat.side = THREE.DoubleSide;

                if (mat.map) {
                    mat.map.colorSpace = THREE.SRGBColorSpace;
                    mat.map.needsUpdate = true;
                }

                if (mat.emissiveMap) {
                    mat.emissiveMap.colorSpace = THREE.SRGBColorSpace;
                    mat.emissiveMap.needsUpdate = true;
                }

                mat.needsUpdate = true;
            });
        });
    }

    // ----------------------------
    // Top hero scene
    // ----------------------------
    const heroScene = new THREE.Scene();

    const heroCamera = new THREE.PerspectiveCamera(
        45,
        heroHost.clientWidth / heroHost.clientHeight,
        0.1,
        1000
    );
    heroCamera.position.set(0, 0, 5);

    const heroRenderer = createRenderer(heroHost, "4");
    addStandardLights(heroScene, "dark");

    let heroModel = null;
    let heroWrapper = null;
    let dropAnimationStart = null;
    const dropDuration = 1400;

    let mouseTargetX = 0;
    let mouseTargetY = 0;
    let mouseCurrentX = 0;
    let mouseCurrentY = 0;
    const maxOffsetX = 0.35;
    const maxOffsetY = 0.22;
    const mouseEase = 0.06;

    loadObjWithMtl({
        objFile: "BLK2GO_Adapter.obj",
        mtlFile: "BLK2GO_Adapter.mtl",
        onLoaded: (obj) => {
            const initialBox = new THREE.Box3().setFromObject(obj);
            const initialSize = initialBox.getSize(new THREE.Vector3());
            const maxAxis = Math.max(initialSize.x, initialSize.y, initialSize.z);

            if (maxAxis > 0) {
                const scale = 1.1 / maxAxis;
                obj.scale.setScalar(scale);
            }

            const box = new THREE.Box3().setFromObject(obj);
            const center = box.getCenter(new THREE.Vector3());

            obj.position.set(-center.x, -center.y, -center.z);
            obj.rotation.x = -0.25;
            obj.rotation.z = 0.12;

            heroModel = obj;
            heroWrapper = new THREE.Group();
            heroWrapper.add(heroModel);
            heroWrapper.position.set(0, 3.5, 0);
            heroScene.add(heroWrapper);

            dropAnimationStart = performance.now();
        },
    });

    heroHost.addEventListener("mousemove", (event) => {
        const rect = heroHost.getBoundingClientRect();
        const x = ((event.clientX - rect.left) / rect.width) * 2 - 1;
        const y = ((event.clientY - rect.top) / rect.height) * 2 - 1;

        mouseTargetX = clamp(-x * maxOffsetX, -maxOffsetX, maxOffsetX);
        mouseTargetY = clamp(-y * maxOffsetY, -maxOffsetY, maxOffsetY);
    });

    heroHost.addEventListener("mouseleave", () => {
        mouseTargetX = 0;
        mouseTargetY = 0;
    });

    // ----------------------------
    // Bottom split-section left model
    // ----------------------------
    const bottomScene = new THREE.Scene();

    const bottomCamera = new THREE.PerspectiveCamera(
        40,
        bottomModelHost.clientWidth / bottomModelHost.clientHeight,
        0.1,
        1000
    );
    bottomCamera.position.set(0, 0.15, 5);

    const bottomRenderer = createRenderer(bottomModelHost, "1");
    addStandardLights(bottomScene, "light");

    let bottomModel = null;
    let bottomWrapper = null;
    let bottomMixer = null;
    const bottomClock = new THREE.Clock();

    // Orbit controls for mouse rotate + zoom
    const bottomControls = new OrbitControls(bottomCamera, bottomRenderer.domElement);
    bottomControls.enableDamping = true;
    bottomControls.dampingFactor = 0.06;
    bottomControls.enablePan = false;
    bottomControls.enableRotate = true;
    bottomControls.enableZoom = true;

    // Limited zoom range
    bottomControls.minDistance = 3.8;
    bottomControls.maxDistance = 6.2;

    // Keep gentle automatic Y rotation
    bottomControls.autoRotate = true;
    bottomControls.autoRotateSpeed = 1.2;

    // Keep interaction centered nicely
    bottomControls.target.set(0, 0, 0);

    // Custom loading manager to force texture lookup into the texture folder
    const manager = new THREE.LoadingManager();

    manager.setURLModifier((url) => {
        if (!url) {
            return url;
        }

        // Already absolute or data URI
        if (
            url.startsWith("http://") ||
            url.startsWith("https://") ||
            url.startsWith("data:") ||
            url.startsWith("/")
        ) {
            return url;
        }

        const lower = url.toLowerCase();

        if (lower.endsWith(".bin")) {
            return `${animatedModelFolder}${url.split("/").pop()}`;
        }

        if (
            lower.endsWith(".jpg") ||
            lower.endsWith(".jpeg") ||
            lower.endsWith(".png") ||
            lower.endsWith(".webp")
        ) {
            return `${animatedTextureFolder}${url.split("/").pop()}`;
        }

        return `${animatedModelFolder}${url}`;
    });

    const gltfLoader = new GLTFLoader(manager);
    gltfLoader.setPath(animatedModelFolder);
    gltfLoader.setResourcePath(animatedTextureFolder);

    gltfLoader.load(
        "scene.gltf",
        (gltf) => {
            const obj = gltf.scene;

            forceBottomModelMaterials(obj);

            obj.traverse((child) => {
                if (child.isMesh) {
                    child.castShadow = false;
                    child.receiveShadow = false;
                }
            });

            const initialBox = new THREE.Box3().setFromObject(obj);
            const initialSize = initialBox.getSize(new THREE.Vector3());
            const maxAxis = Math.max(initialSize.x, initialSize.y, initialSize.z);

            if (maxAxis > 0) {
                const scale = 1.7 / maxAxis;
                obj.scale.setScalar(scale);
            }

            const box = new THREE.Box3().setFromObject(obj);
            const center = box.getCenter(new THREE.Vector3());

            obj.position.set(-center.x, -center.y, -center.z);
            obj.rotation.x = 0;
            obj.rotation.z = 0;

            bottomModel = obj;
            bottomWrapper = new THREE.Group();
            bottomWrapper.add(bottomModel);
            bottomWrapper.position.set(0, 0, 0);
            bottomScene.add(bottomWrapper);

            if (gltf.animations && gltf.animations.length > 0) {
                bottomMixer = new THREE.AnimationMixer(obj);

                const clip = gltf.animations[0];
                const action = bottomMixer.clipAction(clip);

                action.reset();
                action.setLoop(THREE.LoopPingPong, Infinity);
                action.clampWhenFinished = false;
                action.timeScale = 1.0;
                action.enabled = true;
                action.play();

                console.log("Loaded bottom glTF animation clip:", clip.name || "(unnamed)");
                console.log("Animation duration:", clip.duration);
            } else {
                console.warn("No animations found in scene.gltf");
            }
        },
        undefined,
        (error) => {
            console.error("Error loading animated GLTF:", error);
        }
    );

    // ----------------------------
    // Resize
    // ----------------------------
    function onResize() {
        heroCamera.aspect = heroHost.clientWidth / heroHost.clientHeight;
        heroCamera.updateProjectionMatrix();
        heroRenderer.setSize(heroHost.clientWidth, heroHost.clientHeight);

        bottomCamera.aspect = bottomModelHost.clientWidth / bottomModelHost.clientHeight;
        bottomCamera.updateProjectionMatrix();
        bottomRenderer.setSize(bottomModelHost.clientWidth, bottomModelHost.clientHeight);
    }

    window.addEventListener("resize", onResize);

    // ----------------------------
    // Animation loop
    // ----------------------------
    function animate(now) {
        requestAnimationFrame(animate);

        const delta = bottomClock.getDelta();

        if (heroWrapper) {
            if (dropAnimationStart !== null) {
                const elapsed = now - dropAnimationStart;
                const t = clamp(elapsed / dropDuration, 0, 1);
                const eased = easeOutCubic(t);
                heroWrapper.position.y = 3.5 * (1 - eased);

                if (t >= 1) {
                    dropAnimationStart = null;
                    heroWrapper.position.y = 0;
                }
            }

            mouseCurrentX += (mouseTargetX - mouseCurrentX) * mouseEase;
            mouseCurrentY += (mouseTargetY - mouseCurrentY) * mouseEase;

            heroWrapper.position.x = mouseCurrentX;
            if (dropAnimationStart === null) {
                heroWrapper.position.y = mouseCurrentY;
            }

            if (heroModel) {
                heroModel.rotation.y += 0.01;
            }
        }

        if (bottomMixer) {
            bottomMixer.update(delta);
        }

        bottomControls.update();

        heroRenderer.render(heroScene, heroCamera);
        bottomRenderer.render(bottomScene, bottomCamera);
    }

    requestAnimationFrame(animate);
});