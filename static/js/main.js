// Variáveis globais
let selectedVehicle = null;
let searchTimeout = null;

// Event Listeners
document.addEventListener('DOMContentLoaded', function() {
    console.log('DOM carregado, configurando event listeners...'); // Debug

    // Inicializa elementos do DOM
    const plateSearch = document.getElementById('plate');
    const searchSuggestions = document.getElementById('searchSuggestions');
    const registerAndEntryBtn = document.getElementById('registerAndEntryBtn');
    const registerAndExitBtn = document.getElementById('registerAndExitBtn');
    const entryButton = document.getElementById('entryButton');
    const exitButton = document.getElementById('exitButton');
    const recentRecordsTable = document.getElementById('recentRecords');
    const quickRegisterForm = document.getElementById('quickRegisterForm');
    const quickPlateInput = document.getElementById('quickPlate');
    const quickNameInput = document.getElementById('quickName');
    const quickSectorInput = document.getElementById('quickSector');
    const quickVehicleTypeInput = document.getElementById('quickVehicleType');
    const quickRegisterModal = document.getElementById('quickRegisterModal');

    console.log('Elementos encontrados:', {
        plateSearch,
        searchSuggestions,
        registerAndEntryBtn,
        registerAndExitBtn,
        entryButton,
        exitButton,
        recentRecordsTable,
        quickRegisterForm
    });

    if (!plateSearch || !searchSuggestions) {
        console.log('Elementos de busca não encontrados - provavelmente não estamos na página inicial');
        return;
    }

    // Função para selecionar veículo
    function selectVehicle(vehicle) {
        console.log('Veículo selecionado:', vehicle); // Debug
        selectedVehicle = {
            id: vehicle.id,
            plate: vehicle.plate,
            name: vehicle.name,
            sector: vehicle.sector,
            vehicle_type: vehicle.vehicle_type
        };
        plateSearch.value = vehicle.plate;
        searchSuggestions.innerHTML = '';
        if (entryButton) entryButton.disabled = false;
        if (exitButton) exitButton.disabled = false;
    }

    // Função para abrir modal de cadastro rápido
    function openQuickRegisterModal(plate) {
        if (quickPlateInput) {
            quickPlateInput.value = plate;
            const modal = new bootstrap.Modal(quickRegisterModal);
            modal.show();
        }
    }

    // Função para mostrar sugestões de veículos
    async function showSuggestions(query) {
        if (!query) {
            searchSuggestions.innerHTML = '';
            return;
        }

        try {
            const response = await fetch(`/api/search-vehicles?q=${encodeURIComponent(query)}`);
            if (!response.ok) {
                throw new Error('Erro na busca');
            }

            const vehicles = await response.json();
            
            if (vehicles.length === 0) {
                searchSuggestions.innerHTML = `
                    <div class="suggestion-item no-results">
                        <div class="d-flex justify-content-between align-items-center">
                            <span>Nenhum veículo encontrado</span>
                            <button class="btn btn-sm btn-primary" onclick="openQuickRegisterModal('${query}')">
                                <i class="fas fa-plus me-1"></i>Cadastrar
                            </button>
                        </div>
                    </div>
                `;
                return;
            }

            searchSuggestions.innerHTML = vehicles.map(vehicle => `
                <div class="suggestion-item" onclick="selectVehicle({
                    id: ${vehicle.id},
                    plate: '${vehicle.plate}',
                    name: '${vehicle.name}',
                    sector: '${vehicle.sector}',
                    vehicle_type: '${vehicle.vehicle_type}'
                })">
                    <div class="d-flex justify-content-between align-items-center">
                        <div>
                            <div class="plate-display ${/^[A-Z]{3}[0-9][A-Z][0-9]{2}$/.test(vehicle.plate) ? 'mercosul' : 'antiga'}">
                                ${vehicle.plate}
                            </div>
                            <small class="text-muted">${vehicle.name} - ${vehicle.sector || 'Sem setor'}</small>
                        </div>
                        <small class="vehicle-type">
                            <i class="fas ${vehicle.vehicle_type === 'moto' ? 'fa-motorcycle' : 'fa-car'}"></i>
                        </small>
                    </div>
                </div>
            `).join('');

        } catch (error) {
            console.error('Erro:', error);
            searchSuggestions.innerHTML = '<div class="suggestion-item error">Erro ao buscar veículos</div>';
        }
    }

    // Função para carregar registros recentes
    async function loadRecentRecords() {
        if (!recentRecordsTable) {
            console.log('Tabela de registros recentes não encontrada - provavelmente não estamos na página inicial');
            return;
        }

        try {
            const response = await fetch('/api/recent-records');
            if (!response.ok) {
                throw new Error('Erro ao carregar registros recentes');
            }

            const records = await response.json();
            
            recentRecordsTable.innerHTML = records.map(record => `
                <tr>
                    <td>${record.timestamp}</td>
                    <td>
                        <div class="plate-display ${/^[A-Z]{3}[0-9][A-Z][0-9]{2}$/.test(record.plate) ? 'mercosul' : 'antiga'}">
                            ${record.plate}
                        </div>
                    </td>
                    <td>${record.name}</td>
                    <td>${record.sector || '-'}</td>
                    <td>
                        <span class="badge ${record.record_type === 'ENTRADA' ? 'bg-success' : 'bg-danger'}">
                            ${record.record_type === 'ENTRADA' ? 'ENTRADA' : 'SAÍDA'}
                        </span>
                    </td>
                </tr>
            `).join('');

        } catch (error) {
            console.error('Erro:', error);
            if (recentRecordsTable) {
                recentRecordsTable.innerHTML = '<tr><td colspan="5" class="text-center text-danger">Erro ao carregar registros</td></tr>';
            }
        }
    }

    // Função para registrar entrada/saída
    async function registerRecord(vehicle, recordType) {
        if (!vehicle) {
            showToast('error', 'Nenhum veículo selecionado');
            return;
        }

        try {
            const response = await fetch('/api/records', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify({
                    vehicle_id: vehicle.id,
                    record_type: recordType
                })
            });

            const data = await response.json();

            if (!response.ok) {
                throw new Error(data.error || `Erro ao registrar ${recordType.toLowerCase()}`);
            }

            // Limpa o campo de busca e mantém o foco
            plateSearch.value = '';
            selectedVehicle = null;
            plateSearch.focus();

            // Atualiza a lista de registros
            await loadRecentRecords();

            showToast('success', `${recordType} registrada com sucesso!`);
        } catch (error) {
            console.error('Erro:', error);
            showToast('error', error.message);
        }
    }

    // Função para mostrar mensagens toast
    function showToast(type, message) {
        const toastContainer = document.createElement('div');
        toastContainer.style.position = 'fixed';
        toastContainer.style.top = '20px';
        toastContainer.style.right = '20px';
        toastContainer.style.zIndex = '9999';

        const toast = document.createElement('div');
        toast.className = `alert alert-${type === 'error' ? 'danger' : 'success'} alert-dismissible fade show`;
        toast.role = 'alert';
        toast.innerHTML = `
            ${message}
            <button type="button" class="btn-close" data-bs-dismiss="alert" aria-label="Close"></button>
        `;

        toastContainer.appendChild(toast);
        document.body.appendChild(toastContainer);

        // Remove o toast após 5 segundos
        setTimeout(() => {
            toast.classList.remove('show');
            setTimeout(() => toastContainer.remove(), 150);
        }, 5000);
    }

    // Função para registrar veículo e criar registro
    async function registerAndRecord(recordType) {
        if (!quickRegisterForm) return;

        // Previne múltiplos cliques
        if (registerAndEntryBtn) registerAndEntryBtn.disabled = true;
        if (registerAndExitBtn) registerAndExitBtn.disabled = true;

        try {
            const plate = quickPlateInput?.value;
            const name = quickNameInput?.value;
            const sector = quickSectorInput?.value;
            const vehicleType = quickVehicleTypeInput?.value;

            if (!plate || !name || !sector || !vehicleType) {
                throw new Error('Todos os campos são obrigatórios');
            }

            // Registra o veículo
            console.log('Enviando dados do veículo:', { plate, name, sector, vehicleType });
            const vehicleResponse = await fetch('/api/vehicles', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ 
                    plate: plate.toUpperCase(),
                    name: name.trim(),
                    sector: sector.trim(),
                    vehicle_type: vehicleType
                })
            });

            const vehicleData = await vehicleResponse.json();
            
            if (!vehicleResponse.ok) {
                throw new Error(vehicleData.error || 'Erro ao cadastrar veículo');
            }

            // Registra a entrada/saída
            console.log('Enviando dados do registro:', { vehicle_id: vehicleData.id, record_type: recordType });
            const recordResponse = await fetch('/api/records', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    vehicle_id: vehicleData.id,
                    record_type: recordType
                })
            });

            const recordData = await recordResponse.json();
            
            if (!recordResponse.ok) {
                throw new Error(recordData.error || 'Erro ao registrar ' + recordType.toLowerCase());
            }

            // Atualiza a lista de registros
            await loadRecentRecords();

            // Fecha o modal e limpa o formulário
            const modal = bootstrap.Modal.getInstance(quickRegisterModal);
            if (modal) modal.hide();
            quickRegisterForm.reset();

            // Limpa o campo de busca e mantém o foco
            if (plateSearch) {
                plateSearch.value = '';
                selectedVehicle = null;
                plateSearch.focus();
            }

            // Mostra mensagem de sucesso
            showToast('success', 'Veículo cadastrado e ' + recordType.toLowerCase() + ' registrada com sucesso!');
        } catch (error) {
            console.error('Erro:', error);
            showToast('error', error.message);
        } finally {
            // Reativa os botões
            if (registerAndEntryBtn) registerAndEntryBtn.disabled = false;
            if (registerAndExitBtn) registerAndExitBtn.disabled = false;
        }
    }

    // Event listeners do modal
    if (registerAndEntryBtn) {
        registerAndEntryBtn.addEventListener('click', async (e) => {
            e.preventDefault();
            e.stopPropagation();
            await registerAndRecord('ENTRADA');
        }, { once: false });
    }

    if (registerAndExitBtn) {
        registerAndExitBtn.addEventListener('click', async (e) => {
            e.preventDefault();
            e.stopPropagation();
            await registerAndRecord('SAÍDA');
        }, { once: false });
    }

    // Event listener para o formulário de cadastro rápido
    if (quickRegisterForm) {
        quickRegisterForm.addEventListener('submit', (e) => {
            e.preventDefault();
            e.stopPropagation();
        });
    }

    // Carrega os registros recentes quando a página carrega
    loadRecentRecords();

    // Evento de digitação no campo de busca
    plateSearch.addEventListener('input', function() {
        const query = this.value.trim().toUpperCase();
        clearTimeout(searchTimeout);
        searchTimeout = setTimeout(() => showSuggestions(query), 300);
    });

    // Adiciona os event listeners para os botões
    console.log('Botões encontrados:', { entryButton, exitButton, registerAndEntryBtn, registerAndExitBtn }); // Debug
    
    if (entryButton) {
        entryButton.addEventListener('click', () => {
            console.log('Clique no botão de entrada'); // Debug
            registerRecord(selectedVehicle, 'ENTRADA');
        });
    }
    
    if (exitButton) {
        exitButton.addEventListener('click', () => {
            console.log('Clique no botão de saída'); // Debug
            registerRecord(selectedVehicle, 'SAÍDA');
        });
    }

    // Fecha as sugestões quando clicar fora
    document.addEventListener('click', function(e) {
        if (searchSuggestions && !e.target.closest('.search-container')) {
            searchSuggestions.innerHTML = '';
        }
    });

    // Torna as funções globais
    window.selectVehicle = selectVehicle;
    window.openQuickRegisterModal = openQuickRegisterModal;
    window.showToast = showToast;

});
