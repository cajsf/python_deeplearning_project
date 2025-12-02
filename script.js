const API_BASE = "http://127.0.0.1:8000/api";
let authToken = localStorage.getItem("token");

const Toast = Swal.mixin({
    toast: true,
    position: 'top-end',       // 우측 상단에 표시
    showConfirmButton: false,  // 확인 버튼 없음
    timer: 2000,               // 2초 뒤 자동 사라짐
    timerProgressBar: true,
    didOpen: (toast) => {
        toast.addEventListener('mouseenter', Swal.stopTimer)
        toast.addEventListener('mouseleave', Swal.resumeTimer)
    }
});

// 25개 알레르기 전체 리스트
const allAllergiesList = [
    {id: 1, name: "난류"}, {id: 2, name: "가금류"}, {id: 3, name: "계란"}, {id: 4, name: "소고기"}, 
    {id: 5, name: "쇠고기"}, {id: 6, name: "돼지고기"}, {id: 7, name: "닭고기"}, {id: 8, name: "새우"}, 
    {id: 9, name: "게"}, {id: 10, name: "오징어"}, {id: 11, name: "고등어"}, {id: 12, name: "조개류"}, 
    {id: 13, name: "굴"}, {id: 14, name: "전복"}, {id: 15, name: "홍합"}, {id: 16, name: "우유"}, 
    {id: 17, name: "땅콩"}, {id: 18, name: "호두"}, {id: 19, name: "잣"}, {id: 20, name: "대두"}, 
    {id: 21, name: "복숭아"}, {id: 22, name: "토마토"}, {id: 23, name: "밀"}, {id: 24, name: "메밀"}, 
    {id: 25, name: "이황산류"}
];

const allergyGroups = [
    { name: "계란·가금류", desc: "계란, 닭고기, 난류", icon: "fa-egg", ids: [1, 2, 3, 7] }, 
    { name: "육류", desc: "소, 돼지, 쇠고기", icon: "fa-bacon", ids: [4, 5, 6] },
    { name: "해산물/어패류", desc: "새우, 게, 조개, 생선", icon: "fa-fish", ids: [8, 9, 10, 11, 12, 13, 14, 15] },
    { name: "유제품", desc: "우유", icon: "fa-cow", ids: [16] },
    { name: "견과류", desc: "땅콩, 호두, 잣", icon: "fa-tree", ids: [17, 18, 19] },
    { name: "곡물·두류", desc: "밀, 대두, 메밀", icon: "fa-wheat-awn", ids: [20, 23, 24] },
    { name: "과일·채소", desc: "복숭아, 토마토", icon: "fa-carrot", ids: [21, 22] },
    { name: "첨가물", desc: "이황산류", icon: "fa-flask", ids: [25] }
];

let selectedAllergens = new Set();
let myAllergyIds = new Set();
let currentPage = 1;
let currentQuery = "";
let isIdVerified = false; // 중복 확인 완료 여부

// ================= 로그아웃 (최상단 배치) =================
function logout() {
    Swal.fire({
        text: "로그아웃 하시겠습니까?",
        icon: 'warning',
        showCancelButton: true,
        confirmButtonColor: '#10B981',
        cancelButtonColor: '#d33',
        confirmButtonText: '네',
        cancelButtonText: '아니요'
    }).then((result) => {
        if (result.isConfirmed) {
            localStorage.clear();
            authToken = null;
            window.location.href = "index.html";
        }
    });
}

// ================= 페이지 로드 시 실행 =================
window.onload = async () => {
    // 1. 마이페이지 로직
    if (document.getElementById('myAllergyContainer')) {
        if (!authToken) { alert("로그인이 필요합니다."); window.location.href = "index.html"; return; }
        await fetchMyInfoForMyPage();
    }

    // 2. 메인/검색 페이지 로직
    if (document.getElementById('filterContainer')) {
        renderFilters();
        checkLoginStatus(); // 상단바 업데이트
        
        const searchInput = document.getElementById("searchInput");
        if (searchInput) {
            searchInput.addEventListener("keypress", (e) => { if (e.key === "Enter") handleSearch(); });
        }

        if (window.location.pathname.includes("search.html")) {
            const params = new URLSearchParams(window.location.search);
            const q = params.get('q');
            const avoid = params.getAll('avoid');

            if (q) {
                currentQuery = q;
                document.getElementById('searchInput').value = q;
                avoid.forEach(id => {
                    selectedAllergens.add(parseInt(id));
                    allergyGroups.forEach(g => {
                        if(g.ids.includes(parseInt(id))) {
                            const btn = document.getElementById(`group-btn-${g.name}`);
                            if(btn) activateBtnStyle(btn);
                        }
                    });
                });
                await fetchAndRender();
            }
        }
    }

    // 3. 관리자 페이지 로직
    if (document.getElementById('totalUserCount')) {
        if (!authToken) { alert("관리자 로그인이 필요합니다."); window.location.href = "index.html"; return; }
        await loadAdminDashboard();
    }
};

function resetIdCheck() {
    isIdVerified = false;
    const msg = document.getElementById('idCheckMsg');
    msg.classList.add('hidden');
    msg.className = "text-xs mt-1 font-bold hidden"; // 클래스 초기화
}

// ================= [핵심] 마이페이지 최적화 로직 (캐싱 + 프로필 수정) =================

function loadProfileFromCache() {
    const cName = localStorage.getItem("cached_nickname");
    const cUser = localStorage.getItem("cached_username");
    const cImg = localStorage.getItem("cached_profile_image");
    const cRole = localStorage.getItem("cached_role");

    if (document.getElementById('profileName') && cName) document.getElementById('profileName').innerText = cName;
    if (document.getElementById('profileUsername') && cUser) document.getElementById('profileUsername').innerText = cUser;
    
    const roleEl = document.getElementById('userRole');
    if (roleEl && cRole) {
        if (cRole === 'admin') {
            roleEl.innerHTML = '<span class="text-emerald-600 font-bold">👑 관리자 (Admin)</span>';
            const adminBtn = document.getElementById('adminBtn');
            if (adminBtn) adminBtn.classList.remove('hidden');
        } else roleEl.innerText = '일반 회원';
    }
    const imgEl = document.getElementById('profileImage');
    if (imgEl && cImg && cImg !== "null") imgEl.src = `http://127.0.0.1:8000${cImg}`;
}

function saveProfileToCache(nick, user, role, img) {
    localStorage.setItem("cached_nickname", nick);
    localStorage.setItem("cached_username", user);
    localStorage.setItem("cached_role", role);
    localStorage.setItem("cached_profile_image", img);
}

async function fetchMyInfoForMyPage() {
    loadProfileFromCache();
    try {
        const res = await fetch(`${API_BASE}/users/me`, { headers: { 'Authorization': `Bearer ${authToken}` } });
        if (!res.ok) throw new Error("정보 로드 실패");
        const data = await res.json();
        
        const dispName = data.user.nickname || data.user.username;
        document.getElementById('profileName').innerText = dispName;
        document.getElementById('profileUsername').innerText = data.user.username;
        
        const roleEl = document.getElementById('userRole');
        if (roleEl) {
            if (data.user.role === 'admin') {
                roleEl.innerHTML = '<span class="text-emerald-600 font-bold">👑 관리자 (Admin)</span>';
                const adminBtn = document.getElementById('adminBtn');
                if (adminBtn) adminBtn.classList.remove('hidden');
            } else roleEl.innerText = '일반 회원';
        }
        
        const imgEl = document.getElementById('profileImage');
        if (data.user.profile_image) imgEl.src = `http://127.0.0.1:8000${data.user.profile_image}`;
        else imgEl.src = "https://via.placeholder.com/150?text=USER";

        saveProfileToCache(dispName, data.user.username, data.user.role, data.user.profile_image);
        myAllergyIds.clear();
        data.allergies.forEach(a => myAllergyIds.add(a.allergy_id));
        renderMyPageChips();
    } catch (e) { if (e.message === "정보 로드 실패") logout(); }
}

function renderMyPageChips() {
    const container = document.getElementById('myAllergyContainer');
    if(!container) return;
    document.getElementById('allergyCount').innerText = `${myAllergyIds.size}개 선택됨`;
    container.innerHTML = "";
    allAllergiesList.forEach(a => {
        const hasIt = myAllergyIds.has(a.id);
        const btn = document.createElement('button');
        btn.className = `setting-chip w-full py-3 px-2 rounded-xl border text-sm transition flex items-center justify-center gap-2 ${hasIt ? "active" : "bg-white border-slate-200 text-slate-600 hover:bg-slate-50"}`;
        btn.innerHTML = hasIt ? `<i class="fa-solid fa-check"></i> ${a.name}` : a.name;
        btn.onclick = () => toggleMyAllergy(a.id);
        container.appendChild(btn);
    });
}

async function toggleMyAllergy(id) {
    try {
        if (myAllergyIds.has(id)) {
            await fetch(`${API_BASE}/users/me/allergies/${id}`, { method: 'DELETE', headers: { 'Authorization': `Bearer ${authToken}` } });
            myAllergyIds.delete(id);
        } else {
            const res = await fetch(`${API_BASE}/users/me/allergies`, { method: 'POST', headers: { 'Content-Type': 'application/json', 'Authorization': `Bearer ${authToken}` }, body: JSON.stringify({ allergy_id: id }) });
            if (!res.ok) throw new Error("실패");
            myAllergyIds.add(id);
        }
        renderMyPageChips();
    } catch (e) { alert("오류 발생"); }
}

// ------------------- [추가된 마이페이지 기능들] -------------------

// script.js의 uploadProfileImage 함수를 이걸로 덮어쓰세요

async function uploadProfileImage(input) {
    // 파일이 선택되었는지 확인
    if (input.files && input.files[0]) {
        const formData = new FormData();
        formData.append("file", input.files[0]);

        try {
            const res = await fetch(`${API_BASE}/users/me/profile`, {
                method: "PUT",
                headers: { "Authorization": `Bearer ${authToken}` },
                body: formData
            });

            if (res.ok) {
                const data = await res.json();
                
                // 1. 캐시 데이터 최신화 (이미지 경로 업데이트)
                // (기존 정보들은 유지하고 이미지만 바꿉니다)
                const currentName = document.getElementById('profileName').innerText;
                const currentUser = document.getElementById('profileUsername').innerText;
                const currentRole = localStorage.getItem("cached_role");
                const currentAllergies = JSON.parse(localStorage.getItem("cached_allergies") || "[]");
                
                saveProfileToCache(currentName, currentUser, currentRole, data.profile_image, currentAllergies);

                // 2. [수정됨] 예쁜 알림창 띄우기
                await Swal.fire({
                    title: '프로필 사진 변경 완료!',
                    text: '새로운 이미지가 적용되었습니다.',
                    icon: 'success',
                    confirmButtonColor: '#10B981', // Emerald-500 색상
                    confirmButtonText: '확인'
                });

                // 3. 확인 누르면 새로고침 (상단바 아이콘까지 싹 바뀌게)
                location.reload();

            } else {
                Swal.fire('실패', '이미지 업로드에 실패했습니다.', 'error');
            }
        } catch (e) {
            console.error(e);
            Swal.fire('오류', '서버 통신 중 오류가 발생했습니다.', 'error');
        }
    }
}

function editNickname() { document.getElementById('nicknameForm').classList.toggle('hidden'); }

async function saveNickname() {
    const newNick = document.getElementById('newNicknameInput').value;
    if(!newNick) return alert("닉네임을 입력하세요");
    const formData = new FormData(); formData.append("nickname", newNick);
    try {
        const res = await fetch(`${API_BASE}/users/me/profile`, {
            method: "PUT", headers: { "Authorization": `Bearer ${authToken}` }, body: formData
        });
        if(res.ok) {
            document.getElementById('profileName').innerText = newNick;
            document.getElementById('nicknameForm').classList.add('hidden');
            // 캐시 업데이트
            const currentUser = document.getElementById('profileUsername').innerText;
            const currentImgPath = document.getElementById('profileImage').src.replace("http://127.0.0.1:8000", "").split("?")[0];
            saveProfileToCache(newNick, currentUser, null, currentImgPath);
            alert("닉네임이 변경되었습니다.");
        } else alert("변경 실패");
    } catch(e) { alert("오류"); }
}

function togglePwForm() { document.getElementById('pwForm').classList.toggle('hidden'); }

// script.js 의 changePassword 함수 교체

// script.js 의 changePassword 함수 교체

async function changePassword() {
    const cPw = document.getElementById('currentPw').value;
    const nPw = document.getElementById('newPw').value;
    const cfPw = document.getElementById('confirmPw').value;

    if (!cPw || !nPw) return Swal.fire('입력 오류', '모든 항목을 입력해주세요.', 'warning');
    if (nPw !== cfPw) return Swal.fire('불일치', '새 비밀번호가 일치하지 않습니다.', 'warning');

    // 1. [변경 전 질문] 정말 바꿀 건지 먼저 물어봅니다.
    const confirmResult = await Swal.fire({
        text: "정말로 비밀번호를 변경하시겠습니까?",
        icon: 'question',
        showCancelButton: true,
        confirmButtonColor: '#10B981',
        cancelButtonColor: '#94a3b8',
        confirmButtonText: '변경하기',
        cancelButtonText: '취소'
    });

    if (!confirmResult.isConfirmed) return;

    try {
        const res = await fetch(`${API_BASE}/users/me/password`, {
            method: "PUT",
            headers: {
                "Content-Type": "application/json",
                "Authorization": `Bearer ${authToken}`
            },
            body: JSON.stringify({
                current_password: cPw,
                new_password: nPw
            })
        });

        if (res.ok) {
            // 2. [변경 후 강제 로그아웃]
            // logout() 함수를 부르지 않고, 여기서 직접 정보를 지우고 튕겨냅니다.
            await Swal.fire({
                title: '변경 완료',
                text: '보안을 위해 다시 로그인해주세요.',
                icon: 'success',
                confirmButtonColor: '#10B981',
                confirmButtonText: '확인'
            });

            // 캐시 삭제 및 메인 이동 (질문 없이 즉시 실행)
            localStorage.clear();
            authToken = null;
            window.location.href = "index.html";

        } else {
            const e = await res.json();
            Swal.fire('변경 실패', e.detail, 'error');
        }
    } catch (e) {
        Swal.fire('오류', '서버 통신 중 오류가 발생했습니다.', 'error');
    }
}

// ================= 인증 및 상단바 UI (Navbar) =================
function checkLoginStatus() {
    const authSection = document.getElementById('authSection');
    if (!authSection) return;
    if (authToken) {
        authSection.innerHTML = `<div class="animate-pulse flex items-center gap-2"><div class="w-8 h-8 bg-slate-200 rounded-full"></div><div class="w-20 h-4 bg-slate-200 rounded"></div></div>`;
        fetchUserInfoForNavbar();
    } else {
        authSection.innerHTML = `
            <button onclick="openModal('loginModal')" class="text-slate-600 hover:bg-slate-100 font-medium rounded-lg text-sm px-4 py-2 transition whitespace-nowrap">로그인</button>
            <button onclick="openModal('registerModal')" class="text-white bg-emerald-500 hover:bg-emerald-600 font-medium rounded-lg text-sm px-4 py-2 shadow-md transition whitespace-nowrap">회원가입</button>
        `;
        myAllergyIds.clear();
    }
}

async function fetchUserInfoForNavbar() {
    try {
        const res = await fetch(`${API_BASE}/users/me`, { headers: { 'Authorization': `Bearer ${authToken}` } });
        if (!res.ok) throw new Error();
        const data = await res.json();
        myAllergyIds.clear();
        data.allergies.forEach(a => myAllergyIds.add(a.allergy_id));

        const authSection = document.getElementById('authSection');
        if (authSection) {
            const initial = data.user.username.charAt(0).toUpperCase();
            let profileImgHtml = `<div class="w-8 h-8 bg-emerald-500 rounded-full flex items-center justify-center text-white text-sm font-bold border-2 border-emerald-100 group-hover:bg-emerald-600 transition">${initial}</div>`;
            if(data.user.profile_image) profileImgHtml = `<img src="http://127.0.0.1:8000${data.user.profile_image}" class="w-8 h-8 rounded-full border-2 border-emerald-100 object-cover">`;

            authSection.innerHTML = `
                <div class="flex items-center gap-3 bg-white border border-slate-200 rounded-full pl-1 pr-4 py-1 shadow-sm hover:shadow-md transition">
                    <a href="mypage.html" class="flex items-center gap-2 group" title="마이페이지">
                        ${profileImgHtml}
                        <div class="flex flex-col justify-center">
                            <span class="text-xs font-bold text-slate-700 leading-none group-hover:text-emerald-600 transition">${data.user.nickname || data.user.username}</span>
                            <span class="text-[10px] text-slate-400 leading-none mt-0.5">내 정보</span>
                        </div>
                    </a>
                    <div class="h-4 w-px bg-slate-200"></div>
                    <button onclick="logout()" class="text-xs text-slate-400 hover:text-red-500 font-medium transition" title="로그아웃"><i class="fa-solid fa-arrow-right-from-bracket text-sm"></i></button>
                </div>
            `;
        }
        const welcomeMsg = document.getElementById('welcomeMsg');
        if(welcomeMsg) welcomeMsg.innerHTML = `<span class="text-emerald-600 font-bold">${data.user.nickname || data.user.username}</span>님, <span class="text-red-500 font-bold">등록된 알레르기(${data.allergies.length}개)</span>를 기준으로 안전한 식품을 찾아드릴게요.`;
        
        if (document.getElementById('filterContainer')) {
            allergyGroups.forEach(group => {
                if (group.ids.some(id => myAllergyIds.has(id))) {
                    const btn = document.getElementById(`group-btn-${group.name}`);
                    if (btn && !btn.classList.contains('active')) toggleGroup(btn, group.ids);
                }
            });
        }
    } catch (e) { logout(); }
}

// ================= 검색 & 필터 로직 =================
function renderFilters() {
    const container = document.getElementById('filterContainer');
    if (!container) return;
    container.innerHTML = "";
    allergyGroups.forEach(group => {
        const btn = document.createElement('button');
        btn.id = `group-btn-${group.name}`;
        btn.className = `filter-chip px-3 py-1.5 rounded-full border border-slate-200 bg-white text-slate-600 hover:border-emerald-400 hover:text-emerald-600 transition flex items-center gap-2 text-xs font-bold shadow-sm`;
        btn.innerHTML = `<i class="fa-solid ${group.icon} text-sm"></i><span>${group.name}</span>`;
        btn.onclick = () => toggleGroup(btn, group.ids);
        container.appendChild(btn);
    });
}

function toggleGroup(btn, ids) {
    const isSelected = ids.some(id => selectedAllergens.has(id));
    if (isSelected) {
        ids.forEach(id => selectedAllergens.delete(id));
        deactivateBtnStyle(btn);
    } else {
        ids.forEach(id => selectedAllergens.add(id));
        activateBtnStyle(btn);
    }
}
function activateBtnStyle(btn) { btn.classList.add('active'); btn.classList.remove('bg-white', 'text-slate-600', 'border-slate-200'); }
function deactivateBtnStyle(btn) { btn.classList.remove('active'); btn.classList.add('bg-white', 'text-slate-600', 'border-slate-200'); }

function handleSearch() {
    const query = document.getElementById('searchInput').value;
    if (!query) {
        Swal.fire({
            icon: 'warning',
            text: '검색어를 입력해주세요.',
            showConfirmButton: false,
            timer: 700
        });
        return; }
    const params = new URLSearchParams();
    params.append('q', query);
    selectedAllergens.forEach(id => params.append('avoid', id));
    if (window.location.pathname.includes("search.html")) {
        currentQuery = query; currentPage = 1;
        window.history.pushState({}, "", `search.html?${params.toString()}`);
        document.getElementById('resultGrid').innerHTML = "";
        document.getElementById('loadMoreBtn').classList.add('hidden');
        document.getElementById('loading').classList.remove('hidden');
        fetchAndRender();
    } else { window.location.href = `search.html?${params.toString()}`; }
}

async function loadMore() { currentPage++; await fetchAndRender(); }

// script.js - fetchAndRender 함수 전체 교체

async function fetchAndRender() {
    let url = `${API_BASE}/food/search?q=${currentQuery}&page=${currentPage}&limit=12`;
    selectedAllergens.forEach(id => url += `&avoid=${id}`);
    const headers = authToken ? { 'Authorization': `Bearer ${authToken}` } : {};
    
    try {
        const res = await fetch(url, { headers });
        const data = await res.json();
        
        // 데이터 확인용 로그 (F12 콘솔에서 확인 가능)
        console.log("검색 결과 데이터:", data);

        document.getElementById('loading').classList.add('hidden');
        if(document.getElementById('resultCount')) document.getElementById('resultCount').innerText = data.length > 0 ? `${data.length}개 검색됨` : "0건";
        
        const grid = document.getElementById('resultGrid');
        
        if (data.length === 0 && currentPage === 1) {
            grid.innerHTML = `<div class="col-span-full text-center py-20"><i class="fa-regular fa-face-sad-tear text-4xl text-slate-300 mb-4"></i><p class="text-slate-500">검색 결과가 없습니다.</p></div>`;
            return;
        }

        data.forEach(item => {
            let badgeHTML = "";
            let cardClass = "border-slate-100 hover:border-emerald-300";
            let imgBg = "bg-slate-50";
            let iconColor = "text-slate-300";
            
            // 뱃지 로직 (기존과 동일)
            const foodAllergies = item.allergy_ids || [];
            let isDanger = false;
            if (authToken && myAllergyIds.size > 0) {
                if (foodAllergies.some(id => myAllergyIds.has(id))) {
                    isDanger = true;
                    badgeHTML = `<span class="absolute top-3 right-3 bg-red-500 text-white text-[10px] font-bold px-2 py-1 rounded-full shadow-md flex items-center gap-1 z-10 animate-pulse"><i class="fa-solid fa-triangle-exclamation"></i> 위험</span>`;
                    cardClass = "border-red-100 hover:border-red-300 ring-1 ring-red-50";
                    imgBg = "bg-red-50";
                    iconColor = "text-red-200";
                }
            }
            if (!isDanger && ((authToken && myAllergyIds.size > 0) || selectedAllergens.size > 0)) {
                badgeHTML = `<span class="absolute top-3 right-3 bg-emerald-500 text-white text-[10px] font-bold px-2 py-1 rounded-full shadow-md flex items-center gap-1 z-10"><i class="fa-solid fa-check"></i> 안심</span>`;
                imgBg = "bg-emerald-50";
                iconColor = "text-emerald-200";
            }

            // [핵심 수정] 이미지 주소 생성
            const hasImg = item.food_img_url && item.food_img_url !== "";
            let finalImgUrl = "";
            
            if (hasImg) {
                // DB 경로가 /static/... 으로 시작하면 도메인을 붙여줍니다.
                finalImgUrl = `http://127.0.0.1:8000${item.food_img_url}`;
                // 디버깅: 이미지 주소가 제대로 만들어졌는지 콘솔에 출력
                // console.log("이미지 로딩 시도:", finalImgUrl);
            }

            const card = document.createElement('div');
            card.className = `bg-white rounded-2xl shadow-sm border ${cardClass} overflow-hidden cursor-pointer group relative transition-all duration-300 hover:shadow-lg hover:-translate-y-1`;
            card.onclick = () => openModal('detailModal', item.food_id);
            
            // [핵심 수정] onerror 제거! (이미지가 깨져도 일단 태그를 숨기지 않음)
            card.innerHTML = `
                ${badgeHTML}
                <div class="h-40 w-full ${imgBg} flex items-center justify-center overflow-hidden relative">
                    ${hasImg 
                        ? `<img src="${finalImgUrl}" 
                                class="w-full h-full object-cover group-hover:scale-105 transition duration-500" 
                                alt="${item.food_name}" 
                                loading="lazy">` 
                        : `<i class="fa-solid fa-utensils text-5xl ${iconColor} group-hover:scale-110 transition duration-500"></i>`
                    }
                </div>
                <div class="p-5">
                    <p class="text-xs text-slate-400 font-medium mb-1">ID: ${item.food_id}</p>
                    <h3 class="text-lg font-bold text-slate-800 leading-tight mb-2 group-hover:text-emerald-600 transition line-clamp-2">${item.food_name}</h3>
                    <div class="flex items-center justify-between mt-4 pt-4 border-t border-slate-50"><span class="text-xs text-slate-500">상세 분석</span><div class="w-8 h-8 rounded-full bg-slate-50 flex items-center justify-center text-slate-400 group-hover:bg-emerald-500 group-hover:text-white transition"><i class="fa-solid fa-arrow-right text-xs"></i></div></div>
                </div>
            `;
            grid.appendChild(card);
        });
        if(data.length > 0) document.getElementById('loadMoreBtn').classList.remove('hidden');
    } catch (e) { console.error(e); alert("데이터 로드 오류"); }
}

// ================= 로그인/회원가입 =================
async function checkIdDuplicate() {
    const username = document.getElementById('regId').value;
    const msg = document.getElementById('idCheckMsg');

    if (!username) {
        alert("아이디를 입력해주세요.");
        return;
    }

    try {
        // API 호출
        const res = await fetch(`${API_BASE}/auth/check-username?username=${username}`);
        const data = await res.json();

        msg.classList.remove('hidden');
        
        if (data.available) {
            // 사용 가능
            msg.innerText = "✅ 사용 가능한 아이디입니다.";
            msg.className = "text-xs mt-1 font-bold text-emerald-500";
            isIdVerified = true;
        } else {
            // 사용 불가
            msg.innerText = "❌ 이미 사용 중인 아이디입니다.";
            msg.className = "text-xs mt-1 font-bold text-red-500";
            isIdVerified = false;
        }
    } catch (e) {
        console.error(e);
        alert("서버 통신 오류");
    }
}

async function login() {
    const username = document.getElementById('loginId').value;
    const password = document.getElementById('loginPw').value;
    try {
        const formData = new FormData(); formData.append('username', username); formData.append('password', password);
        const res = await fetch(`${API_BASE}/auth/login`, { method: 'POST', body: formData });
        if (!res.ok) throw new Error();
        const data = await res.json();
        localStorage.setItem("token", data.access_token);
        authToken = data.access_token;
        closeModal('loginModal');
        location.reload();
    } catch (e) { alert("아이디 또는 비밀번호가 올바르지 않습니다."); }
}

async function register() {
    const username = document.getElementById('regId').value;
    const nickname = document.getElementById('regNick').value;
    const password = document.getElementById('regPw').value;
    const confirmPw = document.getElementById('regPwConfirm').value;

    if (!username || !password || !confirmPw) {
        return Swal.fire('입력 오류', '필수 항목을 모두 입력해주세요.', 'warning');
    }

    // [핵심] 중복 확인 안 했으면 막기
    if (!isIdVerified) {
        return Swal.fire('중복 확인 필요', '아이디 중복 확인 버튼을 눌러주세요.', 'warning');
    }

    if (password !== confirmPw) {
        return Swal.fire('불일치', '비밀번호가 서로 다릅니다.', 'error');
    }

    try {
        const res = await fetch(`${API_BASE}/auth/register`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ 
                username: username, 
                password: password,
                nickname: nickname || username 
            })
        });

        if (res.ok) {
            await Swal.fire({
                icon: 'success',
                title: '가입 환영합니다!',
                text: '이제 로그인해주세요.',
                confirmButtonColor: '#10B981'
            });
            closeModal('registerModal');
            document.getElementById('loginId').value = username;
            openModal('loginModal');
        } else {
            const err = await res.json();
            Swal.fire('가입 실패', err.detail, 'error');
        }
    } catch (e) {
        Swal.fire('오류', '서버 통신 중 문제가 발생했습니다.', 'error');
    }
}

async function deleteAccount() {
    // 1. [안전 장치] 정말 탈퇴할 것인지 먼저 물어봅니다.

    // 2. [본인 확인] 비밀번호 입력 받기
    const { value: pwd } = await Swal.fire({
        title: '비밀번호 확인',
        input: 'password',
        inputLabel: '본인 확인을 위해 비밀번호를 입력해주세요.',
        inputPlaceholder: '비밀번호',
        showCancelButton: true,
        confirmButtonText: '탈퇴하기',
        confirmButtonColor: '#d33',
        cancelButtonText: '취소'
    });

    // 비밀번호를 입력하지 않고 취소했으면 종료
    if (!pwd) return;

    const confirmResult = await Swal.fire({
        title: '정말 탈퇴하시겠습니까?',
        text: "탈퇴 시 모든 데이터가 삭제되며 복구할 수 없습니다.",
        icon: 'warning',
        showCancelButton: true,
        confirmButtonColor: '#d33', // 빨간색 (경고)
        cancelButtonColor: '#94a3b8', // 회색 (취소)
        confirmButtonText: '네, 탈퇴하겠습니다',
        cancelButtonText: '취소'
    });

    // 취소했으면 함수 종료
    if (!confirmResult.isConfirmed) return;
    // 3. [API 호출] 삭제 요청
    try {
        const res = await fetch(`${API_BASE}/users/me`, {
            method: 'DELETE',
            headers: { 
                'Content-Type': 'application/json', 
                'Authorization': `Bearer ${authToken}` 
            },
            body: JSON.stringify({ password: pwd })
        });

        if (res.ok) {
            // 4. [성공 시] 묻지 않고 안내 후 바로 강제 로그아웃
            await Swal.fire({
                title: '탈퇴 완료',
                text: '이용해 주셔서 감사합니다.',
                icon: 'success',
                confirmButtonColor: '#10B981',
                confirmButtonText: '확인'
            });

            // 기존 logout() 함수를 부르지 않고(질문 안 함), 직접 초기화 수행
            localStorage.clear();
            authToken = null;
            window.location.href = "index.html"; // 메인으로 튕겨내기

        } else {
            // 비밀번호 틀림 등 에러 처리
            const errorData = await res.json().catch(() => ({ detail: "삭제 실패" }));
            Swal.fire('탈퇴 실패', errorData.detail || '비밀번호가 일치하지 않습니다.', 'error');
        }
    } catch (e) {
        console.error(e);
        Swal.fire('오류', '서버 통신 중 오류가 발생했습니다.', 'error');
    }
}
// ================= 관리자 페이지 =================
async function loadAdminDashboard() {
    try {
        const resStats = await fetch(`${API_BASE}/admin/stats`, { headers: { 'Authorization': `Bearer ${authToken}` } });
        if (resStats.status === 403) { alert("권한 없음"); location.href = "index.html"; return; }
        const stats = await resStats.json();
        const statsContainer = document.getElementById('topAllergyStats');
        statsContainer.innerHTML = "";
        let maxCount = stats.length > 0 ? stats[0].registration_count : 1;
        stats.forEach((item, index) => {
            const percent = (item.registration_count / maxCount) * 100;
            statsContainer.innerHTML += `<div><div class="flex justify-between text-xs mb-1"><span class="font-bold text-slate-700">${index+1}위. ${item.allergy_name}</span><span class="text-slate-500">${item.registration_count}명</span></div><div class="w-full bg-slate-100 rounded-full h-2.5"><div class="${index === 0 ? 'bg-red-500' : 'bg-slate-300'} h-2.5 rounded-full" style="width: ${percent}%"></div></div></div>`;
        });
        const resUsers = await fetch(`${API_BASE}/admin/users`, { headers: { 'Authorization': `Bearer ${authToken}` } });
        const users = await resUsers.json();
        document.getElementById('totalUserCount').innerText = `${users.length}명`;
        const userBody = document.getElementById('userListBody');
        userBody.innerHTML = "";
        users.forEach(u => {
            userBody.innerHTML += `<tr class="border-b border-slate-100 hover:bg-slate-50"><td class="px-4 py-3 font-medium">${u.user_id}</td><td class="px-4 py-3">${u.username}</td><td class="px-4 py-3">${u.role === 'admin' ? '<span class="bg-purple-100 text-purple-700 px-2 py-0.5 rounded text-xs font-bold">관리자</span>' : '<span class="bg-slate-100 text-slate-600 px-2 py-0.5 rounded text-xs">일반</span>'}</td></tr>`;
        });
        const chkContainer = document.getElementById('adminAllergyCheckboxes');
        chkContainer.innerHTML = "";
        allAllergiesList.forEach(a => {
            chkContainer.innerHTML += `<label class="flex items-center space-x-2 bg-white p-2 rounded border border-slate-200 cursor-pointer hover:border-emerald-500"><input type="checkbox" name="newAllergy" value="${a.id}" class="w-4 h-4 text-emerald-600 rounded focus:ring-emerald-500"><span class="text-xs text-slate-600">${a.name}</span></label>`;
        });
    } catch (e) { console.error(e); }
}

async function registerFood() {
    const name = document.getElementById('newFoodName').value;
    const company = document.getElementById('newCompany').value;
    const url = document.getElementById('newUrl').value;
    const checkboxes = document.querySelectorAll('input[name="newAllergy"]:checked');
    const allergyIds = Array.from(checkboxes).map(cb => parseInt(cb.value));
    if (!name || !company) { alert("필수 입력 누락"); return; }
    try {
        const res = await fetch(`${API_BASE}/admin/food`, { method: 'POST', headers: { 'Content-Type': 'application/json', 'Authorization': `Bearer ${authToken}` }, body: JSON.stringify({ food_name: name, company_name: company, food_url: url, allergy_ids: allergyIds }) });
        if (res.ok) { alert("등록 성공"); location.reload(); } else { alert("실패"); }
    } catch (e) { alert("오류"); }
}

// script.js - openModal 함수 전체 교체

async function openModal(modalId, foodId = null) {
    const modal = document.getElementById(modalId);
    if(modal) modal.classList.remove('hidden');
    
    if (modalId === 'detailModal' && foodId) {
        try {
            const headers = authToken ? { 'Authorization': `Bearer ${authToken}` } : {};
            const res = await fetch(`${API_BASE}/food/${foodId}`, { headers });
            const data = await res.json();
            
            document.getElementById('mFoodName').innerText = data.food.food_name;
            document.getElementById('mCompany').innerText = data.food.company_name || "미상";
            document.getElementById('mLink').href = data.food.food_url || "#";

            // [이미지 처리]
            const imgEl = document.getElementById('mFoodImage');
            const iconEl = document.getElementById('mFoodIcon');

            if (data.food.food_img_url) {
                const fullUrl = `http://127.0.0.1:8000${data.food.food_img_url}`;
                console.log("상세 이미지 로딩:", fullUrl); // 콘솔 확인용

                imgEl.src = fullUrl;
                imgEl.classList.remove('hidden'); // 숨김 해제
                if(iconEl) iconEl.classList.add('hidden');
            } else {
                imgEl.classList.add('hidden');    
                if(iconEl) iconEl.classList.remove('hidden'); 
            }

            // 알레르기 정보 등 나머지 로직은 그대로 유지
            const allergyDiv = document.getElementById('mAllergies');
            if (data.allergies.length > 0) {
                allergyDiv.innerHTML = data.allergies.map(a => {
                    const isDanger = myAllergyIds.has(a.allergy_id);
                    const style = isDanger ? "bg-red-600 text-white border-red-700 animate-pulse" : "bg-rose-50 text-rose-600 border-rose-100";
                    return `<span class="px-3 py-1.5 rounded-lg ${style} text-xs font-bold border flex items-center gap-1"><i class="fa-solid fa-circle-exclamation"></i> ${a.allergy_name}</span>`;
                }).join('');
            } else { 
                allergyDiv.innerHTML = `<span class="bg-emerald-50 text-emerald-600 px-3 py-1 rounded-lg text-xs">안전</span>`; 
            }
            
            const crossSec = document.getElementById('mCrossSection');
            if (data.cross_reactions?.length > 0) {
                crossSec.classList.remove('hidden');
                document.getElementById('mCrossText').innerHTML = data.cross_reactions.map(cr => `<strong>${cr.cross_reaction_name}</strong>`).join(', ') + " 알레르기 주의";
            } else { crossSec.classList.add('hidden'); }

        } catch (e) { console.error(e); }
    }
}
// [수정된 함수] 모달 닫을 때 입력값 및 상태 초기화 기능 추가
function closeModal(modalId) {
    const modal = document.getElementById(modalId);
    if (modal) {
        modal.classList.add('hidden'); // 1. 모달 숨기기

        // 2. 모달 안에 있는 모든 input 태그 찾아서 내용 비우기
        const inputs = modal.querySelectorAll('input');
        inputs.forEach(input => {
            input.value = '';
        });

        // 3. 회원가입 모달일 경우, 특별히 초기화해야 할 상태값들 처리
        if (modalId === 'registerModal') {
            // 전역 변수 초기화 (중복확인 여부)
            if (typeof isIdVerified !== 'undefined') {
                isIdVerified = false; 
            }

            // 아이디 중복 확인 메시지 숨기기 & 초기화
            const idMsg = document.getElementById('idCheckMsg');
            if (idMsg) {
                idMsg.innerText = "";
                idMsg.className = "text-xs mt-1 font-bold hidden"; // 클래스 원상복구
                idMsg.classList.add('hidden');
            }

            // 비밀번호 일치 메시지 숨기기 & 초기화
            const pwMsg = document.getElementById('pwMatchMsg');
            if (pwMsg) {
                pwMsg.innerText = "";
                pwMsg.classList.add('hidden');
                pwMsg.className = "text-xs mt-1 font-bold hidden";
            }
        }
    }
}

// ================= [업그레이드] 관리자 제품 관리 로직 =================

let allAdminFoods = []; // 데이터를 저장해둘 전역 변수

// ================= [수정됨] 관리자 제품 관리 (Server-side Search) =================

// 1. 제품 목록 불러오기 (검색어가 있으면 검색, 없으면 전체)
async function loadProductList() {
    try {
        const res = await fetch(`${API_BASE}/admin/foods`, { headers: { 'Authorization': `Bearer ${authToken}` } });
        const foods = await res.json();
        
        const tbody = document.getElementById('foodListBody');
        tbody.innerHTML = "";
        
        if (foods.length === 0) {
            tbody.innerHTML = `<tr><td colspan="4" class="text-center py-4 text-slate-400">등록된 제품이 없습니다.</td></tr>`;
            return;
        }

        foods.forEach(food => {
            tbody.innerHTML += `
                <tr class="border-b border-slate-100 hover:bg-slate-50 transition">
                    <td class="px-4 py-3 font-mono text-xs text-slate-400">#${food.food_id}</td>
                    
                    <td class="px-4 py-3 font-bold text-slate-700">${food.food_name}</td>
                    
                    <td class="px-4 py-3 text-slate-500 text-xs whitespace-nowrap">
                        <span class="bg-slate-100 px-2 py-1 rounded">${food.company_name}</span>
                    </td>
                    
                    <td class="px-4 py-3 text-center whitespace-nowrap">
                        <button onclick="deleteFood(${food.food_id}, '${food.food_name}')" 
                                class="text-red-400 hover:text-white hover:bg-red-500 px-3 py-1 rounded transition text-xs font-bold border border-red-100">
                            삭제
                        </button>
                    </td>
                </tr>
            `;
        });
    } catch (e) { console.error("제품 목록 로드 실패", e); }
}

// 2. 테이블 그리기
function renderAdminFoodTable(data) {
    const tbody = document.getElementById('foodListBody');
    tbody.innerHTML = "";
    
    if (data.length === 0) {
        tbody.innerHTML = `<tr><td colspan="4" class="text-center py-8 text-slate-400">검색 결과가 없습니다.</td></tr>`;
        return;
    }

    data.forEach(food => {
        tbody.innerHTML += `
            <tr class="border-b border-slate-100 hover:bg-slate-50 transition">
                <td class="px-4 py-3 font-mono text-xs text-slate-400">#${food.food_id}</td>
                <td class="px-4 py-3 font-bold text-slate-700">${food.food_name}</td>
                <td class="px-4 py-3 text-slate-500 text-xs">
                    <span class="bg-slate-100 rounded px-2 py-1">${food.company_name}</span>
                </td>
                <td class="px-4 py-3 text-center">
                    <button onclick="deleteFood(${food.food_id}, '${food.food_name}')" 
                            class="text-red-400 hover:text-white hover:bg-red-500 px-3 py-1.5 rounded-lg transition text-xs font-bold border border-red-100 hover:border-red-500">
                        삭제
                    </button>
                </td>
            </tr>
        `;
    });
}

// 3. 엔터키 입력 시 검색 실행
function handleAdminSearch(event) {
    if (event.key === 'Enter') {
        loadProductList();
    }
}

async function deleteFood(id, name) {
    Swal.fire({
        title: '제품 삭제',
        text: `'${name}' 제품을 삭제하시겠습니까?`,
        icon: 'warning',
        showCancelButton: true,
        confirmButtonColor: '#d33',
        cancelButtonColor: '#3085d6',
        confirmButtonText: '삭제',
        cancelButtonText: '취소'
    }).then(async (result) => {
        if (result.isConfirmed) {
            try {
                const res = await fetch(`${API_BASE}/admin/food/${id}`, {
                    method: 'DELETE',
                    headers: { 'Authorization': `Bearer ${authToken}` }
                });
                if (res.ok) {
                    await Swal.fire('삭제됨', '제품이 삭제되었습니다.', 'success');
                    loadProductList();
                } else {
                    Swal.fire('실패', '삭제 실패', 'error');
                }
            } catch (e) { Swal.fire('오류', '서버 오류', 'error'); }
        }
    });
}

// ================= [신규] 구글 스타일 이미지 검색 =================

async function analyzeImage(input) {
    // 1. 파일이 선택되었는지 확인
    if (!input.files || !input.files[0]) return;

    const file = input.files[0];
    const loadingEl = document.getElementById('aiLoading');
    const resultArea = document.getElementById('aiResultArea');

    // 2. UI 준비 (로딩 표시, 이전 결과 숨김)
    loadingEl.classList.remove('hidden');
    resultArea.classList.add('hidden');
    // 검색창에 파일명 표시 (선택사항)
    document.getElementById('searchInput').value = `📷 이미지 분석 중: ${file.name}`;

    try {
        // 3. 서버로 전송할 데이터 준비
        const formData = new FormData();
        formData.append("file", file);

        // 4. API 호출 (로컬+Gemini 하이브리드)
        // (API 주소는 실제 백엔드 주소로 맞춰주세요)
        const res = await fetch(`${API_BASE}/ai/predict`, {
            method: "POST",
            body: formData
        });

        if (!res.ok) throw new Error("AI 분석 실패");
        const data = await res.json();

        // 5. 결과 표시
        renderAiResult(data, file);

    } catch (e) {
        console.error(e);
        alert("이미지 분석 중 오류가 발생했습니다. 다시 시도해주세요.");
        document.getElementById('searchInput').value = ""; // 검색창 초기화
    } finally {
        // 6. 마무리 (로딩 숨김, input 초기화)
        loadingEl.classList.add('hidden');
        input.value = ""; // 같은 파일을 다시 선택할 수 있게 초기화
    }
}

// 분석 결과를 화면에 그리는 함수
function renderAiResult(data, file) {
    const resultArea = document.getElementById('aiResultArea');
    const searchInput = document.getElementById('searchInput');

    // 검색창에 분석된 음식 이름 입력
    searchInput.value = data.name;

    // 위험 여부 판단 (내 알레르기 정보와 대조)
    // (주의: 현재는 재료명 텍스트로 비교하므로 정확도가 낮을 수 있음. 추후 ID 기반으로 고도화 필요)
    let dangerIngredients = [];
    if (authToken && myAllergyIds.size > 0) {
        // 내 알레르기 이름 목록 가져오기
        const myAllergyNames = Array.from(myAllergyIds).map(id => {
            const a = allAllergiesList.find(item => item.id === id);
            return a ? a.name : "";
        }).filter(name => name !== "");

        // AI가 찾은 재료 중에 내 알레르기 성분이 있는지 텍스트로 확인
        dangerIngredients = data.ingredients.filter(ing => 
            myAllergyNames.some(myAllergy => ing.includes(myAllergy))
        );
    }
    const isDanger = dangerIngredients.length > 0;

    // 결과 HTML 생성
    resultArea.innerHTML = `
        <div class="flex flex-col md:flex-row gap-6 items-start">
            <div class="w-32 h-32 rounded-2xl overflow-hidden border-2 ${isDanger ? 'border-red-500' : 'border-emerald-500'} shadow-sm flex-shrink-0">
                <img src="${URL.createObjectURL(file)}" class="w-full h-full object-cover">
            </div>

            <div class="flex-1">
                <div class="flex justify-between items-start mb-3">
                    <div>
                        <p class="text-xs text-slate-500 font-bold mb-1">AI 분석 결과 (${data.source})</p>
                        <h3 class="text-2xl font-bold text-slate-900 leading-tight">${data.name}</h3>
                    </div>
                    <div class="flex-shrink-0 ml-4">
                        ${isDanger 
                            ? `<span class="bg-red-500 text-white px-3 py-1.5 rounded-full text-sm font-bold shadow-sm flex items-center animate-pulse"><i class="fa-solid fa-triangle-exclamation mr-2"></i>위험 감지</span>` 
                            : `<span class="bg-emerald-500 text-white px-3 py-1.5 rounded-full text-sm font-bold shadow-sm flex items-center"><i class="fa-solid fa-check mr-2"></i>안심 가능</span>`
                        }
                    </div>
                </div>

                <div class="mb-4">
                    <p class="text-xs font-bold text-slate-400 uppercase mb-2">감지된 주요 재료</p>
                    <div class="flex flex-wrap gap-2">
                        ${data.ingredients.map(ing => {
                            const isRisky = dangerIngredients.some(danger => ing.includes(danger));
                            return `<span class="${isRisky ? 'bg-red-100 text-red-700 border-red-200' : 'bg-slate-100 text-slate-600 border-slate-200'} border px-2.5 py-1 rounded-lg text-xs font-medium">${ing}</span>`;
                        }).join('')}
                    </div>
                </div>
                
                ${isDanger ? `
                    <div class="bg-red-50 p-3 rounded-xl border border-red-100 text-sm text-red-700 flex items-start">
                        <i class="fa-solid fa-circle-info mt-0.5 mr-2 text-red-500"></i>
                        <span>회원님의 알레르기 유발 성분(<strong>${dangerIngredients.join(', ')}</strong>)이 포함되었을 가능성이 높습니다. 섭취에 주의하세요.</span>
                    </div>
                ` : ''}
                
                <button onclick="handleSearch()" class="w-full mt-4 bg-slate-900 text-white py-3 rounded-xl font-bold hover:bg-slate-800 transition text-sm">
                    '${data.name}'(으)로 상세 검색 결과 보기 <i class="fa-solid fa-arrow-right ml-1"></i>
                </button>

                <div class="mt-4 pt-4 border-t border-slate-100">
                    <p class="text-xs text-slate-400 mb-2 cursor-pointer hover:text-slate-600 flex items-center" onclick="document.getElementById('feedbackForm').classList.toggle('hidden')">
                        <i class="fa-regular fa-face-frown-open mr-1"></i> 결과가 실제와 다른가요? (피드백 보내기)
                    </p>
                    <div id="feedbackForm" class="hidden bg-slate-50 p-3 rounded-xl border border-slate-200">
                        <p class="text-xs text-slate-500 mb-2 font-bold">정확한 음식 이름을 알려주세요. AI 학습에 큰 도움이 됩니다! </p>
                        <div class="flex gap-2">
                            <input type="text" id="correctFoodName" class="w-full p-2 border border-slate-200 rounded-lg text-sm focus:outline-none focus:border-emerald-500" placeholder="예: 김치찌개">
                            <button onclick="sendFeedback('${data.filename}')" class="bg-emerald-500 text-white px-4 py-2 rounded-lg text-sm font-bold hover:bg-emerald-600 transition whitespace-nowrap">
                                제출
                            </button>
                        </div>
                    </div>
                </div>
                </div>
        </div>
    `;

    // 결과 영역 표시
    resultArea.classList.remove('hidden');
}

async function uploadAndAnalyze(input) {
    // 1. 파일이 선택되었는지 확인
    if (!input.files || !input.files[0]) return;

    const file = input.files[0];
    const loadingEl = document.getElementById('loading'); // search.html엔 aiLoading 대신 loading 사용
    const resultArea = document.getElementById('aiResultArea');
    const card = document.getElementById('aiResultCard');
    const preview = document.getElementById('aiPreviewImg');

    // UI 준비
    if(resultArea) resultArea.classList.remove('hidden');
    // search.html 구조에 맞춰 로딩 표시 (aiLoading이 있으면 쓰고, 없으면 메인 로딩 사용)
    const aiLoading = document.getElementById('aiLoading');
    if(aiLoading) aiLoading.classList.remove('hidden');
    else if(loadingEl) loadingEl.classList.remove('hidden');
    
    if(card) card.classList.add('hidden');
    if(preview) preview.src = URL.createObjectURL(file);
    
    // 검색창에 파일명 표시
    const searchInput = document.getElementById('searchInput');
    if(searchInput) searchInput.value = `📷 이미지 분석 중...`;

    try {
        const formData = new FormData();
        formData.append("file", file);

        // API 호출
        const res = await fetch(`${API_BASE}/ai/predict`, {
            method: "POST",
            body: formData
        });

        if (!res.ok) throw new Error("AI 분석 실패");
        const data = await res.json();

        // 결과 렌더링
        renderAiResult(data, file);

    } catch (e) {
        console.error(e);
        alert("이미지 분석 중 오류가 발생했습니다.");
        if(searchInput) searchInput.value = "";
    } finally {
        if(aiLoading) aiLoading.classList.add('hidden');
        else if(loadingEl) loadingEl.classList.add('hidden');
        input.value = ""; // 초기화
    }
}

function searchFromAi() {
    const nameEl = document.getElementById('aiFoodName');
    if(nameEl) {
        const foodName = nameEl.innerText;
        const searchInput = document.getElementById('searchInput');
        if(searchInput) {
            searchInput.value = foodName;
            handleSearch();
        }
    }
}

function closeAiResult() {
    const area = document.getElementById('aiResultArea');
    if(area) area.classList.add('hidden');
}

// [신규] 피드백 전송 함수
async function sendFeedback(filename) {
    const correctName = document.getElementById('correctFoodName').value;
    if (!correctName) return alert("정확한 음식 이름을 입력해주세요.");

    try {
        const res = await fetch(`${API_BASE}/ai/feedback`, {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({
                filename: filename,
                correct_name: correctName
            })
        });

        if (res.ok) {
            alert("소중한 정보를 주셔서 감사합니다! 🙇‍♂️\n입력하신 이름으로 다시 검색합니다.");
            
            // 1. 피드백 UI 변경
            document.getElementById('feedbackForm').innerHTML = `<p class="text-xs text-emerald-600 font-bold"><i class="fa-solid fa-check mr-1"></i> 피드백이 반영되었습니다.</p>`;
            
            // 2. [핵심] 검색창 내용을 올바른 이름으로 변경
            const searchInput = document.getElementById('searchInput');
            searchInput.value = correctName;
            
            // 3. [핵심] 변경된 이름으로 즉시 재검색
            handleSearch();

        } else {
            alert("전송 실패");
        }
    } catch (e) {
        console.error(e);
        alert("오류 발생");
    }
}

// ================= [누락된 기능 복구] 관리자 성분표 스캔 =================

async function scanIngredientLabel(input) {
    // 1. 파일 선택 확인
    if (!input.files || !input.files[0]) return;
    
    const file = input.files[0];
    const btn = document.getElementById('ocrBtn');
    // 버튼이 없을 경우를 대비한 방어 코드
    if (!btn) {
        console.error("OCR 버튼을 찾을 수 없습니다.");
        return;
    }

    const originalText = btn.innerHTML;
    
    // 2. 로딩 표시
    btn.innerHTML = '<i class="fa-solid fa-circle-notch fa-spin"></i> 분석 중...';
    btn.classList.add('opacity-50', 'cursor-not-allowed');
    btn.disabled = true;

    try {
        const formData = new FormData();
        formData.append("file", file);

        // 3. API 호출 (Gemini 이용)
        const res = await fetch(`${API_BASE}/admin/ocr`, {
            method: "POST",
            headers: { 'Authorization': `Bearer ${authToken}` },
            body: formData
        });

        if (res.ok) {
            const data = await res.json();
            
            // 4. 결과 반영: 체크박스 자동 선택
            const checkboxes = document.querySelectorAll('input[name="newAllergy"]');
            // 기존 체크 해제
            checkboxes.forEach(cb => cb.checked = false);

            let count = 0;
            if (data.detected_ids && data.detected_ids.length > 0) {
                data.detected_ids.forEach(id => {
                    const targetCb = document.querySelector(`input[name="newAllergy"][value="${id}"]`);
                    if (targetCb) {
                        targetCb.checked = true;
                        count++;
                    }
                });
                alert(`✅ 분석 완료!\n성분표에서 ${count}개의 알레르기 유발 성분을 찾아 체크했습니다.\n\n(읽은 내용: ${data.raw_text.substring(0, 30)}...)`);
            } else {
                alert("분석 완료: 알레르기 유발 성분이 발견되지 않았습니다.");
            }
        } else {
            alert("분석 실패: 서버 오류");
        }
    } catch (e) {
        console.error(e);
        alert("오류가 발생했습니다.");
    } finally {
        // 5. 원상복구
        btn.innerHTML = originalText;
        btn.classList.remove('opacity-50', 'cursor-not-allowed');
        btn.disabled = false;
        input.value = ""; 
    }
}

// 비밀번호 실시간 확인용 함수
function checkPwMatch() {
    const pw = document.getElementById('regPw').value;
    const cf = document.getElementById('regPwConfirm').value;
    const msg = document.getElementById('pwMatchMsg');

    if (!cf) {
        msg.classList.add('hidden');
        return;
    }

    msg.classList.remove('hidden');
    if (pw === cf) {
        msg.innerText = "✅ 비밀번호가 일치합니다.";
        msg.className = "text-xs mt-1 font-bold text-emerald-500";
    } else {
        msg.innerText = "❌ 비밀번호가 일치하지 않습니다.";
        msg.className = "text-xs mt-1 font-bold text-red-500";
    }
}

// [신규] 공유하기 버튼 기능 (제품 정보 복사)
function shareProduct() {
    // 1. 현재 모달창에 떠 있는 제품 이름과 링크 가져오기
    const foodName = document.getElementById('mFoodName').innerText;
    const foodLink = document.getElementById('mLink').href;
    const company = document.getElementById('mCompany').innerText;

    // 2. 클립보드에 복사할 텍스트 만들기
    const textToCopy = `${foodLink}`;

    // 3. 클립보드에 쓰기
    navigator.clipboard.writeText(textToCopy).then(() => {
        // 성공 시 예쁜 팝업
        Swal.fire({
            icon: 'success',
            title: '복사 완료!',
            showConfirmButton: false,
            timer: 700 // 1.5초 뒤 자동으로 닫힘
        });
    }).catch(err => {
        console.error('복사 실패:', err);
        Swal.fire({
            icon: 'error',
            title: '복사 실패',
            text: '브라우저 권한 문제로 복사하지 못했습니다.'
        });
    });
}