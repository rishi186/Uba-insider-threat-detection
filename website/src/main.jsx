import React from 'react'
import ReactDOM from 'react-dom/client'
import App from './App.jsx'
import './index.css'
import { BrowserRouter } from 'react-router-dom'
import { ThemeProvider } from './context/ThemeContext'
import { RoleProvider } from './context/RoleContext'

ReactDOM.createRoot(document.getElementById('root')).render(
    <React.StrictMode>
        <BrowserRouter>
            <RoleProvider>
                <ThemeProvider>
                    <App />
                </ThemeProvider>
            </RoleProvider>
        </BrowserRouter>
    </React.StrictMode>,
)
