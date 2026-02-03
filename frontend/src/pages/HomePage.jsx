import React from "react";
import aiConvertor from "../img/ai_convertor.png";
import dataCleaning from "../img/cleaner.png";
import dashboarding from "../img/dashboard.png";
import insightGeneration from "../img/insight.png";
import logo from "../img/logo.png";
import { Link } from "react-router-dom";

const HomePage = () => {
  return (
    <div className="min-h-screen bg-gradient-to-br from-blue-50 to-indigo-100 bg-fixed w-full">
      {/* Header */}
      <header className="bg-white shadow-sm w-full">
        <div className="w-full px-6 py-4 flex justify-between items-center">
          <div className="flex items-center space-x-2">
            <img src={logo} alt="AutoDashAI Logo" className="w-15 h-10" />
            <span className="text-2xl font-bold text-blue-600">AutoDashAI</span>
          </div>
          <nav className="flex items-center space-x-6">
            <a href="#" className="text-gray-600 hover:text-blue-600 transition">Help</a>
            <button className="flex items-center justify-center w-10 h-10 rounded-full bg-gray-100 hover:bg-gray-200 transition">
              <svg className="w-6 h-6 text-gray-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M16 7a4 4 0 11-8 0 4 4 0 018 0zM12 14a7 7 0 00-7 7h14a7 7 0 00-7-7z" />
              </svg>
            </button>
          </nav>
        </div>
      </header>

      {/* Hero Section */}
      <section className="py-20 px-6 min-h-[60vh] flex items-center w-full">
        <div className="w-full text-center">
          <h1 className="text-5xl font-bold text-gray-800 mb-6 leading-tight">
            Turn Data into Dashboards –{" "}
            <span className="bg-gradient-to-r from-purple-600 to-blue-500 bg-clip-text text-transparent">
              Instantly.
            </span>
          </h1>
          <p className="text-xl text-gray-600 mb-8 max-w-4xl mx-auto leading-relaxed">
            AutoDashAI is an AI-powered web app that provides autonomous data analysis, dynamic visualization, and actionable insights.
            Experience the future of data analysis with a friendly, futuristic, and light interface.
          </p>
        </div>
      </section>

      {/* Solutions Section */}
      <section className="py-20 bg-white px-6 min-h-[60vh] flex items-center w-full">
        <div className="w-full">
          <h2 className="text-4xl font-bold text-center text-gray-800 mb-8">
            Solutions for Every Industry
          </h2>
          <p className="text-lg text-gray-600 text-center mb-16 max-w-3xl mx-auto leading-relaxed">
            AutoDash AI provides tailored solutions for startups, education, healthcare, and SMEs,
            transforming complex data into beautiful, intuitive dashboards.
          </p>

          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-8 max-w-7xl mx-auto">
            {/* AI Converter */}
            {/* AI Converter */}
            <Link
              to="/ai-conversion"
              className="block bg-white p-8 rounded-xl shadow-lg border border-gray-100 hover:shadow-xl transition h-full text-center hover:scale-105 transform duration-300"
            >
              <img
                src={aiConvertor}
                alt="AI Converter"
                className="w-40 h-45 mx-auto mb-6 object-contain"
              />
              <h3 className="text-2xl font-semibold text-gray-800 mb-4">
                AI Converter
              </h3>
              <p className="text-gray-600 text-lg leading-relaxed">
                Convert PDFs and documents into structured tables using AI analysis.
              </p>
            </Link>

            {/* Data Cleaning */}
            <Link
              to="/data-cleaning"
              className="block bg-white p-8 rounded-xl shadow-lg border border-gray-100 hover:shadow-xl transition h-full text-center hover:scale-105 transform duration-300"
            >
              <img
                src={dataCleaning}
                alt="Data Cleaning"
                className="w-40 h-40 mx-auto mb-6 object-contain" />
              <h3 className="text-2xl font-semibold text-gray-800 mb-4">
                Data Cleaning
              </h3>
              <p className="text-gray-600 text-lg leading-relaxed">
                Clean data by handling missing values and preparing for dashboards.
              </p>
            </Link>


            {/* Dashboard Generation */}
            <Link
              to="/data-cleaning"
              className="block bg-white p-8 rounded-xl shadow-lg border border-gray-100 hover:shadow-xl transition h-full text-center hover:scale-105 transform duration-300"
            >
              <img src={dashboarding} alt="Dashboard Generation" className="w-40 h-40 mx-auto mb-6 object-contain" />
              <h3 className="text-2xl font-semibold text-gray-800 mb-4">Start Dashboard</h3>
              <p className="text-gray-600 text-lg leading-relaxed">
                Clean and visualize your data into beautiful, interactive dashboards.
              </p>
            </Link>

            {/* Insight Generation */}
            <Link
              to="/insight-generation"
              className="block bg-white p-8 rounded-xl shadow-lg border border-gray-100 hover:shadow-xl transition h-full text-center hover:scale-105 transform duration-300"
            >
              <img src={insightGeneration} alt="Insight Generation" className="w-40 h-40 mx-auto mb-6 object-contain" />
              <h3 className="text-2xl font-semibold text-gray-800 mb-4">Insight Generation</h3>
              <p className="text-gray-600 text-lg leading-relaxed">
                Generate actionable insights and strategic recommendations.
              </p>
            </Link>
          </div>
        </div>
      </section>

      {/* Footer */}
      <footer className="bg-gray-800 text-white py-12 px-6 w-full">
        <div className="w-full text-center">
          <p className="text-gray-400 text-lg">
            © 2024 AutoDash AI. All rights reserved.
          </p>
        </div>
      </footer>
    </div>
  );
};

export default HomePage;