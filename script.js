const API_BASE = "http://127.0.0.1:8000/api";
let authToken = localStorage.getItem("token");

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

// ================= 로그아웃 (최상단 배치) =================
function logout() {
    if(confirm("로그아웃 하시겠습니까?")) {
        localStorage.removeItem("token");
        localStorage.removeItem("cached_nickname");
        localStorage.removeItem("cached_username");
        localStorage.removeItem("cached_role");
        localStorage.removeItem("cached_profile_image");
        authToken = null;
        window.location.href = "index.html";
    }
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

async function uploadProfileImage(input) {
    if (input.files && input.files[0]) {
        const formData = new FormData();
        formData.append("file", input.files[0]);
        try {
            const res = await fetch(`${API_BASE}/users/me/profile`, {
                method: "PUT", headers: { "Authorization": `Bearer ${authToken}` }, body: formData
            });
            if (res.ok) {
                const data = await res.json();
                document.getElementById('profileImage').src = `http://127.0.0.1:8000${data.profile_image}?t=${new Date().getTime()}`;
                // 캐시 업데이트
                const currentName = document.getElementById('profileName').innerText;
                const currentUser = document.getElementById('profileUsername').innerText;
                saveProfileToCache(currentName, currentUser, null, data.profile_image);
                alert("프로필 사진이 변경되었습니다.");
            } else alert("이미지 업로드 실패");
        } catch (e) { alert("오류 발생"); }
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

async function changePassword() {
    const cPw = document.getElementById('currentPw').value;
    const nPw = document.getElementById('newPw').value;
    const cfPw = document.getElementById('confirmPw').value;
    if(!cPw || !nPw) return alert("모든 항목을 입력해주세요.");
    if(nPw !== cfPw) return alert("새 비밀번호가 일치하지 않습니다.");
    try {
        const res = await fetch(`${API_BASE}/users/me/password`, {
            method: "PUT", headers: { "Content-Type": "application/json", "Authorization": `Bearer ${authToken}` },
            body: JSON.stringify({ current_password: cPw, new_password: nPw })
        });
        if(res.ok) { alert("비밀번호가 변경되었습니다. 다시 로그인해주세요."); logout(); } 
        else { const e = await res.json(); alert("실패: " + e.detail); }
    } catch(e) { alert("오류 발생"); }
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
    if (!query) { alert("검색어를 입력해주세요."); return; }
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

async function fetchAndRender() {
    let url = `${API_BASE}/food/search?q=${currentQuery}&page=${currentPage}&limit=12`;
    selectedAllergens.forEach(id => url += `&avoid=${id}`);
    const headers = authToken ? { 'Authorization': `Bearer ${authToken}` } : {};
    try {
        const res = await fetch(url, { headers });
        const data = await res.json();
        document.getElementById('loading').classList.add('hidden');
        if(document.getElementById('resultCount')) document.getElementById('resultCount').innerText = data.length > 0 ? `${data.length}개 검색됨` : "0건";
        
        if (data.length === 0 && currentPage === 1) {
            document.getElementById('resultGrid').innerHTML = `<div class="col-span-full text-center py-20"><i class="fa-regular fa-face-sad-tear text-4xl text-slate-300 mb-4"></i><p class="text-slate-500">검색 결과가 없습니다.</p></div>`;
            return;
        }
        const grid = document.getElementById('resultGrid');
        data.forEach(item => {
            let badgeHTML = "";
            let cardClass = "border-slate-100 hover:border-emerald-300";
            let imgBg = "bg-slate-50";
            let iconColor = "text-slate-300";
            const foodAllergies = item.allergy_ids || [];
            let isDanger = false;

            if (authToken && myAllergyIds.size > 0) {
                const dangerous = foodAllergies.filter(id => myAllergyIds.has(id));
                if (dangerous.length > 0) {
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

            const card = document.createElement('div');
            card.className = `bg-white rounded-2xl shadow-sm border ${cardClass} overflow-hidden cursor-pointer group relative transition-all duration-300 hover:shadow-lg hover:-translate-y-1`;
            card.onclick = () => openModal('detailModal', item.food_id);
            card.innerHTML = `
                ${badgeHTML}
                <div class="h-40 w-full ${imgBg} flex items-center justify-center overflow-hidden relative">
                    <i class="fa-solid fa-utensils text-5xl ${iconColor} group-hover:scale-110 transition duration-500"></i>
                    ${item.food_url ? '<div class="absolute bottom-2 left-2 bg-black/10 backdrop-blur-sm text-white text-[10px] px-2 py-0.5 rounded">이미지 준비중</div>' : ''}
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
    } catch (e) { console.error(e); alert("API 오류"); }
}

// ================= 로그인/회원가입 =================
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
    const password = document.getElementById('regPw').value;
    try {
        const res = await fetch(`${API_BASE}/auth/register`, { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ username, password }) });
        if (!res.ok) throw new Error((await res.json()).detail);
        alert("가입 성공! 로그인해주세요."); closeModal('registerModal'); openModal('loginModal');
    } catch (e) { alert(e.message); }
}

async function deleteAccount() {
    const pwd = prompt("비밀번호 입력:"); if(!pwd) return;
    try {
        const res = await fetch(`${API_BASE}/users/me`, { method: 'DELETE', headers: { 'Content-Type': 'application/json', 'Authorization': `Bearer ${authToken}` }, body: JSON.stringify({ password: pwd }) });
        if(res.ok) { alert("탈퇴되었습니다."); logout(); } else { alert("실패"); }
    } catch(e) {}
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

// 모달 제어
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
            const allergyDiv = document.getElementById('mAllergies');
            if (data.allergies.length > 0) {
                allergyDiv.innerHTML = data.allergies.map(a => {
                    const isDanger = myAllergyIds.has(a.allergy_id);
                    const style = isDanger ? "bg-red-600 text-white border-red-700 animate-pulse" : "bg-rose-50 text-rose-600 border-rose-100";
                    return `<span class="px-3 py-1.5 rounded-lg ${style} text-xs font-bold border flex items-center gap-1"><i class="fa-solid fa-circle-exclamation"></i> ${a.allergy_name}</span>`;
                }).join('');
            } else { allergyDiv.innerHTML = `<span class="bg-emerald-50 text-emerald-600 px-3 py-1 rounded-lg text-xs">안전</span>`; }
            const crossSec = document.getElementById('mCrossSection');
            if (data.cross_reactions?.length > 0) {
                crossSec.classList.remove('hidden');
                document.getElementById('mCrossText').innerHTML = data.cross_reactions.map(cr => `<strong>${cr.cross_reaction_name}</strong>`).join(', ') + " 주의";
            } else { crossSec.classList.add('hidden'); }
            const altList = document.getElementById('mAlternatives');
            if (data.alternatives?.length > 0) {
                altList.innerHTML = data.alternatives.map(alt => `<li class="p-2 bg-slate-50 rounded-lg text-sm"><i class="fa-solid fa-star text-yellow-400"></i> ${alt}</li>`).join('');
            } else { altList.innerHTML = "<li>없음</li>"; }
        } catch (e) {}
    }
}
function closeModal(modalId) { const modal = document.getElementById(modalId); if(modal) modal.classList.add('hidden'); }

async function loadProductList() {
    try {
        const res = await fetch(`${API_BASE}/admin/foods`, { headers: { 'Authorization': `Bearer ${authToken}` } });
        const foods = await res.json();
        
        const tbody = document.getElementById('foodListBody');
        tbody.innerHTML = "";
        
        if (foods.length === 0) {
            tbody.innerHTML = `<tr><td colspan="4" class="text-center py-4">등록된 제품이 없습니다.</td></tr>`;
            return;
        }

        foods.forEach(food => {
            tbody.innerHTML += `
                <tr class="border-b border-slate-100 hover:bg-slate-50 transition">
                    <td class="px-4 py-3 font-mono text-xs">${food.food_id}</td>
                    <td class="px-4 py-3 font-bold text-slate-700">${food.food_name}</td>
                    <td class="px-4 py-3 text-slate-500">${food.company_name}</td>
                    <td class="px-4 py-3 text-center">
                        <button onclick="deleteFood(${food.food_id}, '${food.food_name}')" 
                                class="text-red-400 hover:text-red-600 hover:bg-red-50 px-3 py-1 rounded transition text-xs font-bold border border-red-100">
                            삭제
                        </button>
                    </td>
                </tr>
            `;
        });
    } catch (e) { console.error("제품 목록 로드 실패", e); }
}

async function deleteFood(id, name) {
    if (!confirm(`정말로 '${name}' 제품을 삭제하시겠습니까?\n삭제하면 복구할 수 없습니다.`)) return;

    try {
        const res = await fetch(`${API_BASE}/admin/food/${id}`, {
            method: 'DELETE',
            headers: { 'Authorization': `Bearer ${authToken}` }
        });

        if (res.ok) {
            alert("삭제되었습니다.");
            loadProductList(); // 목록 새로고침
        } else {
            alert("삭제 실패");
        }
    } catch (e) { alert("서버 오류"); }
}